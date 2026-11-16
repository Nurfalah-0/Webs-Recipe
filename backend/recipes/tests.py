from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Category, Recipe, UserProfile


class RecipeWorkflowAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="Admin_Test_Pass!42",
            is_staff=True,
        )
        self.admin_client = self.authenticated_client(self.admin)
        self.category = Category.objects.create(name="Dinner", slug="dinner")

    def authenticated_client(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def register_member(self, username):
        response = APIClient().post(
            "/api/auth/register/",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password": "Recipe_Test_Pass!947",
                "password_confirm": "Recipe_Test_Pass!947",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "member")
        user = User.objects.get(username=username)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {response.data['token']}"
        )
        return user, client

    def recipe_data(self, title="Noodle soup"):
        return {
            "title": title,
            "description": "A simple recipe",
            "category": self.category.pk,
            "prep_time": 10,
            "cook_time": 20,
            "servings": 2,
        }

    def test_only_creator_can_create_and_manage_own_recipes(self):
        creator, creator_client = self.register_member("creator")
        member, member_client = self.register_member("member")

        self.assertEqual(
            member_client.post(
                "/api/recipes/", self.recipe_data(), format="json"
            ).status_code,
            403,
        )

        response = self.admin_client.patch(
            f"/api/users/{creator.pk}/",
            {"role": UserProfile.CREATOR},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], UserProfile.CREATOR)

        response = creator_client.post(
            "/api/recipes/", self.recipe_data(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        recipe_id = response.data["id"]
        self.assertEqual(response.data["author"], creator.pk)
        self.assertFalse(response.data["is_approved"])

        self.assertEqual(
            member_client.patch(
                f"/api/recipes/{recipe_id}/",
                {"title": "Changed by another member"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            creator_client.patch(
                f"/api/recipes/{recipe_id}/",
                {"title": "Updated by creator"},
                format="json",
            ).status_code,
            200,
        )
        response = creator_client.patch(
            f"/api/recipes/{recipe_id}/",
            {"is_approved": True},
            format="json",
        )
        self.assertFalse(response.data["is_approved"])
        self.assertEqual(
            creator_client.delete(f"/api/recipes/{recipe_id}/").status_code,
            204,
        )

    def test_admin_can_moderate_and_manage_categories_and_users(self):
        creator, creator_client = self.register_member("author")
        self.admin_client.patch(
            f"/api/users/{creator.pk}/",
            {"role": UserProfile.CREATOR},
            format="json",
        )
        created = creator_client.post(
            "/api/recipes/", self.recipe_data(), format="json"
        )
        recipe_url = f"/api/recipes/{created.data['id']}/"

        response = self.admin_client.patch(
            recipe_url, {"is_approved": True}, format="json"
        )
        self.assertTrue(response.data["is_approved"])
        self.assertEqual(APIClient().get("/api/recipes/").data["count"], 1)

        category_response = self.admin_client.post(
            "/api/categories/",
            {"name": "Breakfast", "slug": "breakfast"},
            format="json",
        )
        self.assertEqual(category_response.status_code, 201)
        self.assertEqual(self.admin_client.delete(recipe_url).status_code, 204)

    def test_members_can_bookmark_review_and_logout(self):
        member, member_client = self.register_member("reviewer")
        recipe = Recipe.objects.create(
            author=self.admin,
            category=self.category,
            title="Approved recipe",
            slug="approved-recipe",
            description="Ready to review",
            prep_time=10,
            cook_time=20,
            servings=2,
            is_approved=True,
        )

        bookmark = member_client.post(
            "/api/bookmarks/", {"recipe": recipe.pk}, format="json"
        )
        review = member_client.post(
            "/api/reviews/",
            {"recipe": recipe.pk, "rating": 5, "comment": "Excellent"},
            format="json",
        )
        self.assertEqual(bookmark.status_code, 201)
        self.assertEqual(review.status_code, 201)

        logout_response = member_client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(logout_response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=member).exists())
        self.assertEqual(member_client.get("/api/bookmarks/").status_code, 401)
