# posts/tests/test_urls.py
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus
from django.urls import reverse
from django.core.cache import cache

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        # для проверки доступности адреса group/<slug:slug>/
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='Man_X')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        # Создаем автора поста
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.post.author)

    def test_unexisting_page(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Проверяем доступность страниц для неавторизованного пользователя
    def test_urls_httpstatus_for_guest_user(self):
        """Страницы доступны любому пользователю"""
        urls_list = [
            '/',
            f'/group/{PostURLTests.group.slug}/',
            f'/profile/{PostURLTests.post.author}/',
            f'/posts/{PostURLTests.post.id}/',
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверяем доступность страниц для авторизованного автора
    def test_urls_httpstatus_for_authorized_client_author(self):
        """Страницы доступны авторизованному автору"""
        urls_list = [
            '/',
            f'/group/{PostURLTests.group.slug}/',
            f'/profile/{PostURLTests.post.author}/',
            f'/posts/{PostURLTests.post.id}/',
            '/create/',
            f'/posts/{PostURLTests.post.id}/edit/'
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.authorized_client_author.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверяем редиректы для неавторизованного пользователя
    def test_redirects_for_guest_user(self):
        """Проверяем редиректы для неавторизованного автора"""
        dict_url_redirect = {
            '/create/': reverse('users:login') + '?next='
            + reverse('posts:post_create'),
            f'/posts/{PostURLTests.post.id}/edit/':
            reverse('users:login') + '?next='
            + reverse('posts:post_edit', args=[PostURLTests.post.id])
        }
        for url, redirect in dict_url_redirect.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, redirect)

    def test_redirect_edit_page_for_not_author(self):
        """Страница 'posts/<int:post_id>/edit/' перенаправит не автора поста
        на страницу просмотра поста."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=[PostURLTests.post.id]),
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=[PostURLTests.post.id]
        ))

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostURLTests.post.author}/': 'posts/profile.html',
            f'/posts/{PostURLTests.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{PostURLTests.post.id}/edit/': 'posts/create_post.html',
        }
        for template, adress in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client_author.get(template)
                self.assertTemplateUsed(response, adress)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        # для проверки доступности адреса group/<slug:slug>/
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст 2',
            group=cls.group
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()

    def test_cache_index_page(self):
        '''Тест для проверки кеширования posts:index'''
        # запрашиваем главную страницу
        response = self.guest_client.get(reverse('posts:index'))
        # удаляем пост из базы
        Post.objects.get(text=self.post.text,
                         author=self.post.author).delete()
        # проверяем наличие поста на странице
        self.assertIn(self.post.text, response.content.decode('utf-8'))
        # очищаем кеш
        cache.clear()
        # делаем новый запрос главной странцы
        response = self.guest_client.get(reverse('posts:index'))
        # проверяем отсутствие поста на странице
        self.assertNotIn(self.post.text, response.content.decode('utf-8'))


class TestHandlers(TestCase):
    def test_404_page(self):
        '''Cервер возвращает код 404'''
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
