from django.contrib import admin
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

# Daftarkan model-model ke Django Admin
admin.site.register(Category)
admin.site.register(Ingredient)
admin.site.register(Recipe)
admin.site.register(RecipeIngredient)
admin.site.register(Step)
admin.site.register(Bookmark)
admin.site.register(Review)
admin.site.register(UserProfile)