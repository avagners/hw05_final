import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from http import HTTPStatus
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Comment, Post, Group

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных для проверки сушествующего slug
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
    # Модуль shutil - библиотека Python с удобными инструментами
    # для управления файлами и директориями:
    # создание, удаление, копирование, перемещение, изменение папок и файлов
    # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в таблице Post."""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_data = {
            'text': 'Тестовый текст 2',
            'group': self.group.id,
            'image': uploaded,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse('posts:profile', args=[TaskCreateFormTests.user])
        )
        # Проверяем, сработал ли редирект (проверяем стаус)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем соответствие text, group, author
        first_object = Post.objects.first()
        self.assertEqual(first_object.text, form_data['text'])
        self.assertEqual(
            first_object.group.slug, TaskCreateFormTests.group.slug
        )
        self.assertEqual(
            first_object.author.username, TaskCreateFormTests.user.username
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в таблице Post."""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста 1 отредактирован',
            'group': self.group.id,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[TaskCreateFormTests.post.id]),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', args=[TaskCreateFormTests.post.id]
            )
        )
        # Проверяем, сработал ли редирект (проверяем стаус)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count)
        # Проверяем соответствие text, group, author
        edited_post = Post.objects.first()
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(
            edited_post.group.slug, TaskCreateFormTests.group.slug
        )
        self.assertEqual(
            edited_post.author.username, TaskCreateFormTests.user.username
        )

    def test_create_post_by_guest_client(self):
        """Метод post вызывает редирект для неавторизованного пользователя,
         и что пост не создался"""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст 3',
            'group': self.group.id,
        }
        # Отправляем POST-запрос
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект '/auth/login/?next=/create/'
        self.assertRedirects(
            response, reverse('users:login') + '?next='
            + reverse('posts:post_create')
        )
        # Проверяем, сработал ли редирект (проверяем стаус)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем, кол-во постов не увеличилось
        self.assertEqual(Post.objects.count(), posts_count)


class PostCommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных для проверки сушествующего slug
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
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_add_comment_for_authorized_client(self):
        '''Комментировать посты может только авторизованный пользователь'''
        form_data = {
            'text': 'Тестовый текст комментария'
        }
        comment_count = self.post.comments.count()
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )
        # Проверяем, увеличилось ли число комментариев
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        # Проверяем, проверяем HTTPStatus
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # После успешной отправки комментарий появляется на странице поста
        first_comment = Comment.objects.first()
        self.assertEqual(first_comment.text, form_data['text'])

    def test_add_comment_for_guest_client(self):
        """Метод post вызывает редирект для неавторизованного пользователя,
        и комментарий не создался"""
        form_data = {
            'text': 'Тестовый текст комментария'
        }
        # Отправляем POST-запрос
        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект '/auth/login/?next=/create/'
        self.assertRedirects(
            response, reverse('users:login') + '?next='
            + reverse('posts:post_detail', args=[self.post.id])
            + 'comment/'
        )
        # Проверяем, проверяем HTTPStatus
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем, не увеличилось ли число комментариев
        comment_count = self.post.comments.count()
        self.assertEqual(Comment.objects.count(), comment_count)
