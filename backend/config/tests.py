from django.test import SimpleTestCase
from django.urls import reverse


class PublicPageTests(SimpleTestCase):
    def test_home_page_links_to_api(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Browsable API index")
        self.assertContains(response, "/api/auth/login/")

    def test_login_page_is_available_with_or_without_trailing_slash(self):
        for path in ("/login/", "/login"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=True)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="login-form"')

    def test_favicon_is_served_as_svg(self):
        response = self.client.get(reverse("favicon"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")

    def test_token_login_api_remains_post_only(self):
        response = self.client.get("/api/auth/login/")

        self.assertEqual(response.status_code, 405)
