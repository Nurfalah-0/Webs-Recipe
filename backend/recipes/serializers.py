from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

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


def account_role(user):
    if user.is_staff:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else UserProfile.MEMBER


class AccountSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]

    def get_role(self, user):
        return account_role(user)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]

    def validate(self, attrs):
        password = attrs.get("password")
        if password != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        user = User(
            username=attrs.get("username"),
            email=attrs.get("email", ""),
        )
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        UserProfile.objects.create(user=user, role=UserProfile.MEMBER)
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    ROLE_CHOICES = [
        (UserProfile.MEMBER, "Member"),
        (UserProfile.CREATOR, "Recipe creator"),
        ("admin", "Admin"),
    ]

    role = serializers.ChoiceField(
        choices=ROLE_CHOICES,
        write_only=True,
        required=False,
        default=UserProfile.MEMBER,
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "role",
            "password",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        password = attrs.get("password")
        if self.instance is None and not password:
            raise serializers.ValidationError(
                {"password": "This field is required when creating a user."}
            )
        if password:
            user = self.instance or User(
                username=attrs.get("username"),
                email=attrs.get("email", ""),
            )
            try:
                validate_password(password, user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    {"password": exc.messages}
                ) from exc

        role = attrs.get("role")
        if self.instance and role and role != "admin":
            if self.instance.is_superuser:
                raise serializers.ValidationError(
                    {"role": "A superuser cannot be changed to a non-admin role."}
                )
            if self.instance.is_staff and not User.objects.filter(
                is_staff=True, is_active=True
            ).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError(
                    {"role": "The last active admin cannot be demoted."}
                )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["role"] = account_role(instance)
        return data

    def create(self, validated_data):
        role = validated_data.pop("role", UserProfile.MEMBER)
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password,
            is_staff=role == "admin",
            **validated_data,
        )
        UserProfile.objects.create(
            user=user,
            role=UserProfile.MEMBER if role == "admin" else role,
        )
        return user

    def update(self, instance, validated_data):
        role = validated_data.pop("role", None)
        password = validated_data.pop("password", None)

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        if password:
            instance.set_password(password)
        if role:
            instance.is_staff = role == "admin"
            if role != "admin":
                profile, _ = UserProfile.objects.get_or_create(user=instance)
                profile.role = role
                profile.save(update_fields=["role"])
                instance.profile = profile
        instance.save()
        return instance


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.ReadOnlyField(source="ingredient.name")

    class Meta:
        model = RecipeIngredient
        fields = ["id", "recipe", "ingredient", "ingredient_name", "quantity", "unit"]


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = ["id", "recipe", "step_number", "instruction", "step_image"]


class RecipeSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source="author.username")
    category_name = serializers.ReadOnlyField(source="category.name")
    ingredients = RecipeIngredientSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    steps = StepSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "category",
            "category_name",
            "author",
            "author_username",
            "prep_time",
            "cook_time",
            "servings",
            "difficulty",
            "image",
            "is_approved",
            "created_at",
            "updated_at",
            "ingredients",
            "steps",
        ]
        read_only_fields = ["slug", "author", "is_approved"]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.user.is_staff:
            fields["is_approved"].read_only = False
        return fields


class ReviewSerializer(serializers.ModelSerializer):
    user_username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Review
        fields = [
            "id",
            "recipe",
            "user",
            "user_username",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["user"]


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ["id", "user", "recipe", "created_at"]
        read_only_fields = ["user"]
