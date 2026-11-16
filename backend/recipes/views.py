import logging
from uuid import uuid4

from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.db import DatabaseError, connection
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import filters, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import BaseFilterBackend
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import (
    Bookmark,
    Category,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Review,
    Step,
    UserProfile,
)
from .serializers import (
    AccountSerializer,
    AdminUserSerializer,
    BookmarkSerializer,
    CategorySerializer,
    IngredientSerializer,
    RecipeIngredientSerializer,
    RecipeSerializer,
    RegisterSerializer,
    ReviewSerializer,
    StepSerializer,
)

logger = logging.getLogger(__name__)


def is_recipe_creator(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == UserProfile.CREATOR)


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or bool(
            request.user and request.user.is_staff
        )


class IsRecipeCreatorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_recipe_creator(request.user)

    def has_object_permission(self, request, view, recipe):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            is_recipe_creator(request.user)
            and (
                request.user.is_staff
                or recipe.author_id == request.user.pk
            )
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    owner_attribute = "user"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner_id = getattr(obj, f"{self.owner_attribute}_id", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or owner_id == request.user.pk)
        )


class IsRecipeChildOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_recipe_creator(request.user)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if request.method in permissions.SAFE_METHODS:
            return obj.recipe.is_approved or obj.recipe.author_id == request.user.pk
        return (
            is_recipe_creator(request.user)
            and obj.recipe.author_id == request.user.pk
        )


class RecipeQueryFilterBackend(BaseFilterBackend):
    numeric_filters = (
        "min_prep_time",
        "max_prep_time",
        "min_cook_time",
        "max_cook_time",
    )

    def filter_queryset(self, request, queryset, view):
        category = request.query_params.get("category")
        if category:
            if category.isdecimal():
                queryset = queryset.filter(category_id=int(category))
            else:
                queryset = queryset.filter(category__slug=category)

        difficulty = request.query_params.get("difficulty")
        if difficulty:
            allowed = {value for value, _ in Recipe.DIFFICULTY_CHOICES}
            if difficulty not in allowed:
                raise ValidationError(
                    {"difficulty": f"Choose one of: {', '.join(sorted(allowed))}."}
                )
            queryset = queryset.filter(difficulty=difficulty)

        for parameter in self.numeric_filters:
            value = request.query_params.get(parameter)
            if value is None:
                continue
            try:
                number = int(value)
            except (TypeError, ValueError):
                raise ValidationError({parameter: "Enter a whole number."})
            if number < 0:
                raise ValidationError({parameter: "Must be zero or greater."})

            model_field = parameter[4:]
            lookup = "gte" if parameter.startswith("min_") else "lte"
            queryset = queryset.filter(**{f"{model_field}__{lookup}": number})

        return queryset


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsRecipeCreatorOrAdmin,
    ]
    filter_backends = [
        RecipeQueryFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "title",
        "description",
        "category__name",
        "recipe_ingredients__ingredient__name",
    ]
    ordering_fields = [
        "created_at",
        "updated_at",
        "title",
        "prep_time",
        "cook_time",
        "difficulty",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Recipe.objects.select_related("author", "category").prefetch_related(
            "recipe_ingredients__ingredient",
            "steps",
        )
        user = self.request.user
        if user.is_staff:
            return queryset
        if user.is_authenticated:
            return queryset.filter(Q(is_approved=True) | Q(author=user)).distinct()
        return queryset.filter(is_approved=True)

    def perform_create(self, serializer):
        title_slug = slugify(serializer.validated_data["title"])[:180] or "recipe"
        serializer.save(
            author=self.request.user,
            slug=f"{title_slug}-{uuid4().hex[:12]}",
        )


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = Bookmark.objects.select_related("user", "recipe")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        recipe = serializer.validated_data["recipe"]
        self._ensure_bookmarkable(recipe)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        recipe = serializer.validated_data.get("recipe", serializer.instance.recipe)
        self._ensure_bookmarkable(recipe)
        serializer.save()

    def _ensure_bookmarkable(self, recipe):
        if (
            not self.request.user.is_staff
            and not recipe.is_approved
            and recipe.author_id != self.request.user.pk
        ):
            raise ValidationError(
                {"recipe": "Only approved recipes can be bookmarked."}
            )


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = Review.objects.select_related("user", "recipe")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(
            Q(recipe__is_approved=True) | Q(user=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        recipe = serializer.validated_data["recipe"]
        self._ensure_reviewable(recipe)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        recipe = serializer.validated_data.get("recipe", serializer.instance.recipe)
        self._ensure_reviewable(recipe)
        serializer.save()

    def _ensure_reviewable(self, recipe):
        if (
            not self.request.user.is_staff
            and not recipe.is_approved
            and recipe.author_id != self.request.user.pk
        ):
            raise ValidationError(
                {"recipe": "You can review only approved recipes."}
            )


class RecipeChildViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
        IsRecipeChildOwnerOrAdmin,
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(
            Q(recipe__is_approved=True)
            | Q(recipe__author=self.request.user)
        ).distinct()

    def _ensure_recipe_access(self, recipe):
        if (
            not self.request.user.is_staff
            and recipe.author_id != self.request.user.pk
        ):
            raise PermissionDenied("You can modify steps or ingredients only for your own recipes.")

    def perform_create(self, serializer):
        recipe = serializer.validated_data["recipe"]
        self._ensure_recipe_access(recipe)
        serializer.save()

    def perform_update(self, serializer):
        recipe = serializer.validated_data.get("recipe", serializer.instance.recipe)
        self._ensure_recipe_access(recipe)
        serializer.save()


class RecipeIngredientViewSet(RecipeChildViewSet):
    queryset = RecipeIngredient.objects.all()
    serializer_class = RecipeIngredientSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("recipe", "ingredient")


class StepViewSet(RecipeChildViewSet):
    queryset = Step.objects.all()
    serializer_class = StepSerializer


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response(
            {
                "token": token.key,
                "user": AccountSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValidationError(
                {"detail": "Both username and password are required."}
            )

        user = authenticate(
            request=request,
            username=username,
            password=password,
        )
        if user is None:
            raise ValidationError({"detail": "Invalid username or password."})

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": AccountSerializer(user).data,
            }
        )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile").all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "date_joined", "is_active"]
    ordering = ["username"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError({"detail": "You cannot delete your own account."})
        if instance.is_superuser:
            raise ValidationError(
                {"detail": "Superuser accounts cannot be deleted through this API."}
            )
        if instance.is_staff and not User.objects.filter(
            is_staff=True, is_active=True
        ).exclude(pk=instance.pk).exists():
            raise ValidationError(
                {"detail": "The last active admin cannot be deleted."}
            )
        instance.delete()


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            logger.exception("Database health check failed")
            return Response(
                {"status": "unhealthy", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})

