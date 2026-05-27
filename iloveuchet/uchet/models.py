from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
# Create your models here.


class Roles(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    descrip = models.TextField(blank=True, null=True, verbose_name='Описание')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'


class Departments(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'


class UserManager(BaseUserManager):
    def _create_user(self, contacts, password, **extra_fields):
        if not contacts:
            raise ValueError('Телефон обязателен')

        extra_fields.setdefault('username', contacts)
        user = self.model(contacts=contacts, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, contacts, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(contacts, password, **extra_fields)

    def create_superuser(self, contacts, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')
        return self._create_user(contacts, password, **extra_fields)


class User(AbstractUser):
    lastname = models.CharField(max_length=255, verbose_name='Фамилия')
    firstname = models.CharField(max_length=255, verbose_name='Имя')
    middlename = models.CharField(max_length=255, blank=True, null=True, verbose_name='Отчество')
    contacts = models.CharField(max_length=15, unique=True, verbose_name='Контакты')
    role = models.ForeignKey(
        'Roles',
        on_delete=models.CASCADE,
        verbose_name='Роль'
    )
    department = models.ForeignKey(
        'Departments',
        on_delete=models.CASCADE,
        verbose_name='Отдел'
    )

    objects = UserManager()
    USERNAME_FIELD = 'contacts'
    REQUIRED_FIELDS = ['lastname', 'firstname', 'role', 'department']

    def save(self, *args, **kwargs):
        if not self.username or self.username != self.contacts:
            self.username = self.contacts

        if self.role and self.role.name == 'Администратор':
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.lastname} {self.firstname} {self.middlename or ''}"

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'


class Bids(models.Model):
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Сотрудник'
    )
    problem_text = models.TextField(verbose_name='Проблема')
    time_create = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    time_update = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    STATUSES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('done', 'Завершена')
    ]
    status = models.CharField(max_length=255, choices=STATUSES, verbose_name='Статус')

    resolution = models.TextField(blank=True, null=True, verbose_name='Решение проблемы')
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата принятия')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    accepted_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='accepted_bids', verbose_name='Принял')
    completed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='completed_bids', verbose_name='Завершил')

    def __str__(self):
        return f'№{self.pk}'

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['id']


class Offices(models.Model):
    number = models.CharField(max_length=50, verbose_name='Номер')
    department = models.ForeignKey(
        'Departments',
        on_delete=models.CASCADE,
        verbose_name='Отдел'
    )

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = 'Кабинет'
        verbose_name_plural = 'Кабинеты'


class Categories(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория оборудования'
        verbose_name_plural = 'Категории оборудования'


class Types(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    categories = models.ManyToManyField(Categories, related_name='types', verbose_name='Категории оборудования')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тип комплектующего'
        verbose_name_plural = 'Типы комплектующего'


class Devices(models.Model):
    number = models.CharField(max_length=50, verbose_name='Номер')
    category = models.ForeignKey(
        'Categories',
        on_delete=models.CASCADE,
        verbose_name='Категория оборудования'
    )
    office = models.ForeignKey(
        'Offices',
        on_delete=models.CASCADE,
        verbose_name='Кабинет'
    )

    def __str__(self):
        return f'{self.category.name} {self.number}'

    class Meta:
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудования'


class Components(models.Model):
    model = models.CharField(max_length=255, verbose_name='Модель')
    type = models.ForeignKey(
        'Types',
        on_delete=models.CASCADE,
        verbose_name='Тип'
    )
    counts = models.IntegerField(verbose_name='Количество на складе')

    def __str__(self):
        return self.model

    class Meta:
        verbose_name = 'Комплектующее'
        verbose_name_plural = 'Комплектующие'


class ComponentTransaction(models.Model):
    component = models.ForeignKey('Components', on_delete=models.CASCADE, verbose_name='Комплектующее')
    user = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name='Кто взял')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    taken_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата взятия')
    comment = models.CharField(max_length=255, blank=True, verbose_name='Примечание (например, для какой заявки)')

    class Meta:
        verbose_name = 'Транзакция комплектующего'
        verbose_name_plural = 'Транзакции комплектующих'

