from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    # Master data bahan (misal: Bawang Merah, Tepung Terigu) agar tidak duplikat
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    MEMBER = "member"
    CREATOR = "creator"
    ROLE_CHOICES = [
        (MEMBER, "Member"),
        (CREATOR, "Recipe creator"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=MEMBER
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Recipe(models.Model):
    DIFFICULTY_CHOICES = [
        ("Mudah", "Mudah"),
        ("Sedang", "Sedang"),
        ("Sulit", "Sulit"),
    ]

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipes"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="recipes"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to="recipes/", blank=True, null=True)
    prep_time = models.PositiveIntegerField(
        help_text="Waktu persiapan dalam menit"
    )
    cook_time = models.PositiveIntegerField(
        help_text="Waktu memasak dalam menit"
    )
    servings = models.PositiveIntegerField(help_text="Jumlah porsi")
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="Mudah"
    )
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    # Tabel relasi many-to-many antara Resep dan Bahan beserta takarannya
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(help_text="Jumlah, misal: 2 atau 0.5")
    unit = models.CharField(
        max_length=50, help_text="Satuan, misal: siung, gram, sdm"
    )

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name} untuk {self.recipe.title}"


class Step(models.Model):
    # Langkah-langkah memasak berurutan
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="steps"
    )
    step_number = models.PositiveIntegerField()
    instruction = models.TextField()
    step_image = models.ImageField(
        upload_to="steps/", blank=True, null=True
    )  # Opsional

    class Meta:
        ordering = ["step_number"]

    def __str__(self):
        return f"Langkah {self.step_number} - {self.recipe.title}"


class Bookmark(models.Model):
    # Fitur simpan resep favorit oleh member
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bookmarks"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="bookmarked_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "recipe")  # Mencegah duplikasi bookmark

    def __str__(self):
        return f"{self.user.username} bookmark {self.recipe.title}"


class Review(models.Model):
    # Fitur rating dan komentar oleh member
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)]
    )  # Skala 1 - 5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review oleh {self.user.username} untuk {self.recipe.title} ({self.rating} Bintang)"