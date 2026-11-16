from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminUserViewSet,
    BookmarkViewSet,
    CategoryViewSet,
    IngredientViewSet,
    LoginView,
    RecipeIngredientViewSet,
    RecipeViewSet,
    RegisterView,
    ReviewViewSet,
    StepViewSet,
    LogoutView,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("ingredients", IngredientViewSet, basename="ingredient")
router.register("recipes", RecipeViewSet, basename="recipe")
router.register("bookmarks", BookmarkViewSet, basename="bookmark")
router.register("reviews", ReviewViewSet, basename="review")
router.register("users", AdminUserViewSet, basename="user")
router.register(
    "recipe-ingredients",
    RecipeIngredientViewSet,
    basename="recipe-ingredient",
)
router.register("steps", StepViewSet, basename="step")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("", include(router.urls)),
]
