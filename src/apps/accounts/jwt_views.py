"""JWT Views for User Authentication"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


class JWTTokenObtainPairView(TokenObtainPairView):
    """🔑 JWT: Получение access и refresh токенов"""

    @swagger_auto_schema(
        operation_summary="🔑 Получить JWT токены",
        operation_description="""
        **Аутентификация пользователя и получение JWT токенов**

        Этот endpoint аутентифицирует пользователя по email/паролю и возвращает:
        - Access токен (15 минут) - для API запросов
        - Refresh токен (7 дней) - для обновления access токена

        **Использование access токена:**
        ```
        Authorization: Bearer <access_token>
        ```
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="Email пользователя",
                    example="user@example.com",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description="Пароль пользователя",
                    example="SecurePassword123!",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Токены получены успешно",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="JWT Access токен (15 минут)",
                            example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        ),
                        "refresh": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="JWT Refresh токен (7 дней)",
                            example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        ),
                    },
                ),
            ),
            401: "Неверные учетные данные",
            400: "Ошибка валидации данных",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class JWTTokenRefreshView(TokenRefreshView):
    """🔄 JWT: Обновление access токена"""

    @swagger_auto_schema(
        operation_summary="🔄 Обновить access токен",
        operation_description="""
        **Получить новый access токен используя refresh токен**

        Когда access токен истекает (через 15 минут), используйте этот endpoint
        для получения нового access токена без повторной аутентификации.

        **Безопасность:**
        - Refresh токены ротируются (старый становится недействительным)
        - Если refresh токен истек, нужно заново логиниться
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Действующий JWT refresh токен",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Токен обновлен успешно",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Новый JWT access токен",
                            example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        ),
                    },
                ),
            ),
            401: "Недействительный или истекший refresh токен",
            400: "Неверный формат токена",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class JWTTokenVerifyView(TokenVerifyView):
    """✅ JWT: Проверка валидности токена"""

    @swagger_auto_schema(
        operation_summary="✅ Проверить токен",
        operation_description="""
        **Проверить валидность JWT токена**

        Используйте этот endpoint для проверки:
        - Не истек ли токен
        - Правильно ли подписан токен
        - Не заблокирован ли токен

        **Применение:**
        - Валидация перед критическими операциями
        - Проверки в frontend приложениях
        - Отладка проблем с токенами
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token"],
            properties={
                "token": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="JWT токен для проверки (access или refresh)",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Токен действителен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "token_type": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Тип проверенного токена", example="access"
                        ),
                    },
                ),
            ),
            401: "Токен недействителен или истек",
            400: "Неверный формат токена",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class JWTTokenBlacklistView(TokenBlacklistView):
    """🚫 JWT: Блокировка refresh токена (Logout)"""

    @swagger_auto_schema(
        operation_summary="🚫 Заблокировать токен",
        operation_description="""
        **Добавить refresh токен в черный список (logout)**

        Этот endpoint блокирует refresh токен, что эффективно завершает сессию
        пользователя. После блокировки:
        - Refresh токен нельзя использовать для обновления access токена
        - Access токен продолжает работать до истечения времени
        - Для получения новых токенов нужно заново логиниться

        **Использование:**
        - Logout пользователя
        - Реакция на инциденты безопасности
        - Отзыв скомпрометированных токенов
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="JWT refresh токен для блокировки",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Токен заблокирован успешно",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(
                            type=openapi.TYPE_STRING, example="Токен успешно добавлен в черный список"
                        ),
                    },
                ),
            ),
            400: "Недействительный формат токена или уже заблокирован",
            401: "Токен недействителен",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
