import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.paginator import Page
from django.test import Client, TestCase
from http import HTTPStatus
from django.urls import reverse
from django import forms
from math import ceil

from posts.models import Post, Group, Follow

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание'
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        Post.objects.bulk_create([
            Post(
                author=cls.user,
                text=f'Тестовый текст {num}',
                group=cls.group,
                image=cls.uploaded,
            )
            for num in range(1, 3)
        ])
        cls.post = Post.objects.first()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
    # Модуль shutil - библиотека Python с удобными инструментами
    # для управления файлами и директориями:
    # создание, удаление, копирование, перемещение, изменение папок и файлов
    # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем автора поста
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.post.author)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': (
                reverse('posts:group_list', args=[PostPagesTests.group.slug])
            ),
            'posts/post_detail.html': (
                reverse('posts:post_detail', args=[PostPagesTests.post.id])
            ),
            'posts/profile.html': (
                reverse('posts:profile', args=[PostPagesTests.user])
            ),
            'posts/create_post.html': [
                reverse('posts:post_edit', args=[PostPagesTests.post.id]),
                reverse('posts:post_create'),
            ],
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(template=template, reverse_name=reverse_name):
                if template == 'posts/create_post.html':
                    for item in reverse_name:
                        response = self.authorized_client_author.get(item)
                        self.assertTemplateUsed(response, template)
                else:
                    response = self.authorized_client_author.get(reverse_name)
                    self.assertTemplateUsed(response, template)

    # Проверка словаря контекста главной страницы (в нём передаётся форма)
    def test_home_page_show_correct_context(self):
        """Шаблон home сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(reverse('posts:index'))
        page_obj = response.context.get('page_obj')
        task_img = page_obj[0].image
        self.assertIsInstance(page_obj, Page)
        self.assertIsInstance(page_obj[0], Post)
        self.assertEqual(task_img, PostPagesTests.post.image)

    # Проверка словаря контекста страницы profile
    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(
            reverse('posts:profile', args=[PostPagesTests.post.author])
        )
        page_obj = response.context.get('page_obj')
        task_img = page_obj[0].image
        self.assertEqual(task_img, PostPagesTests.post.image)

    # Проверка словаря контекста страницы profile
    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(
            reverse('posts:post_detail', args=[PostPagesTests.post.id])
        )
        page_obj = response.context.get('post')
        task_img = page_obj.image
        self.assertEqual(task_img, PostPagesTests.post.image)

    # Проверяем, что словарь context страницы group_list
    # в первом элементе списка group_list содержит ожидаемые значения
    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args=[PostPagesTests.group.slug])
        )
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        first_object = response.context['group']
        second_object = response.context['page_obj'][0]
        group_title = first_object.title
        group_slug = first_object.slug
        group_description = first_object.description
        task_img = second_object.image
        self.assertEqual(group_title, PostPagesTests.group.title)
        self.assertEqual(group_slug, PostPagesTests.group.slug)
        self.assertEqual(group_description, PostPagesTests.group.description)
        self.assertEqual(task_img, PostPagesTests.post.image)

    def test_group_list_page_list_is_1(self):
        # Удостоверимся, что на страницу со group_list передаётся
        # ожидаемое количество объектов
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args=[PostPagesTests.group.slug])
        )
        self.assertEqual(len(response.context['page_obj']), 2)
        self.assertIsInstance(response.context['page_obj'][0], Post)

    def test_profile_list_page_list_is_1(self):
        # Удостоверимся, что на страницу со posts:profile передаётся
        # ожидаемое количество объектов
        response = self.authorized_client_author.get(
            reverse('posts:profile', args=[PostPagesTests.post.author])
        )
        self.assertEqual(
            len(response.context['page_obj']),
            Post.objects.count() % settings.COUNT_POSTS
        )
        self.assertIsInstance(response.context['page_obj'][0], Post)

    def test_post_detail_page_list_is_1(self):
        # Удостоверимся, что на страницу post_detail передаётся
        # один пост, отфильтрованный по id
        response = self.authorized_client_author.get(
            reverse('posts:post_detail', args=[PostPagesTests.post.id])
        )
        self.assertIsInstance(response.context['post'], Post)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(
            reverse('posts:post_create')
        )
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(
            reverse('posts:post_edit', args=[PostPagesTests.post.id])
        )
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    # Здесь создаются фикстуры: клиент и 13 тестовых записей.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание'
        )
        Post.objects.bulk_create([
            Post(
                author=cls.user,
                text=f'Тестовый текст {num}',
                group=cls.group
            )
            for num in range(1, 24)
        ])
        cls.post = Post.objects.first()
        cls.post_list = Post.objects.all()
        cls.num_last_page = ceil(Post.objects.count() / settings.COUNT_POSTS)

    def setUp(self):
        # Создаем автора поста
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.post.author)

    def test_index_first_page_contains_ten_records(self):
        response = self.authorized_client_author.get(
            reverse('posts:index')
        )
        # Проверка index количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']), settings.COUNT_POSTS
        )

    def test_index_last_page_contains_three_records(self):
        # Проверка index на последней странице должно быть три поста.
        response = self.authorized_client_author.get(
            reverse('posts:index')
            + f'?page={PaginatorViewsTest.num_last_page}'
        )
        self.assertEqual(
            len(response.context['page_obj']),
            PaginatorViewsTest.post_list.count() % settings.COUNT_POSTS
        )

    def test_group_list_first_page_contains_ten_records(self):
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args=[PaginatorViewsTest.group.slug])
        )
        # Проверка group_list количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']), settings.COUNT_POSTS
        )

    def test_group_list_last_page_contains_three_records(self):
        # Проверка group_list на последней странице должно быть три поста.
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args=[PaginatorViewsTest.group.slug])
            + f'?page={PaginatorViewsTest.num_last_page}'
        )
        self.assertEqual(
            len(response.context['page_obj']),
            PaginatorViewsTest.post_list.count() % settings.COUNT_POSTS
        )

    def test_group_list_first_page_contains_ten_records(self):
        response = self.authorized_client_author.get(
            reverse('posts:profile', args=[PaginatorViewsTest.post.author])
        )
        # Проверка posts:profile количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']), settings.COUNT_POSTS
        )

    def test_profile_last_page_contains_three_records(self):
        '''Проверка posts:profile на последней
        странице должно быть три поста.'''
        response = self.authorized_client_author.get(
            reverse('posts:profile', args=[PaginatorViewsTest.post.author])
            + f'?page={PaginatorViewsTest.num_last_page}'
        )
        self.assertEqual(
            len(response.context['page_obj']),
            PaginatorViewsTest.post_list.count() % settings.COUNT_POSTS
        )


class FollowingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем пользователей и тестовый пост
        cls.user1 = User.objects.create_user(username='Petr')
        cls.user2 = User.objects.create_user(username='Viktoria')
        cls.user3 = User.objects.create_user(username='Semen')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user1,
            text='Тестовый текст',
            group=cls.group
        )

    def setUp(self):
        # Создаем авторизованный клиент user2
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user2)

    def test_follow(self):
        '''Авторизованный пользователь может подписываться'''
        # Подписываемся на user1 (автор единственного поста)
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.user1}))
        # Проверяем кол-во подписок в базе
        self.assertEqual(Follow.objects.count(), 1)

    def test_unfollow(self):
        '''Авторизованный пользователь может удалять подписки'''
        # Отписываемся от user1 (автор единственного поста)
        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user1}))
        # Проверяем кол-во подписок в базе
        self.assertEqual(Follow.objects.count(), 0)

    def test_new_post_for_followers(self):
        '''Новая запись пользователя появляется в ленте
        тех, кто на него подписан'''
        # Подписываемся на user1 (автор единственного поста)
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.user1}))
        # Запрашиваем страницу follow_index
        response = self.authorized_client.get(reverse('posts:follow_index'))
        # Проверяем доступ страницы для авторизованного пользователя
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем наличие поста в ленте
        self.assertContains(response, self.post)

    def test_new_post_for_not_followers(self):
        '''Новая запись пользователя не появляется в ленте
        тех, кто не подписан'''
        # Создаем новый пост от пользователя, которого нет подписки
        new_post = Post.objects.create(
            author=self.user3,
            text='''Пост пользователя, на который
            не подписан авторизованный пользователь.'''
        )
        response = self.authorized_client.get(reverse("posts:follow_index"))
        # Проверяем доступ ленты для авторизованного пользователя
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем отсутствие поста в ленте
        # подписок авторизованного пользователя
        self.assertNotContains(response, new_post)
