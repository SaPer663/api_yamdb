from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from reviews.models import Category, Comment, Genre, GenreTitle, Review, Title
from .tokens import default_token_generator

User = get_user_model()


class SignupUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username', 'email',)
        extra_kwargs = {'email': {'required': True}}

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                f'Пользователь с почтой {value} уже есть в базе'
            )
        return value

    def validate_username(self, value):
        if value == 'me':
            raise serializers.ValidationError(
                'Использовать имя `me` в качестве username запрещено.'
            )
        return value


class TokenSerializer(serializers.Serializer):

    confirmation_code = serializers.CharField(max_length=30)
    username = serializers.CharField(max_length=30)

    def validate(self, data):
        user = get_object_or_404(
            User,
            username=data.get('username')
        )
        if not default_token_generator.check_token(
            user=user,
            token=data.get('confirmation_code')
        ):
            raise serializers.ValidationError(
                'Неверный `confirmation_code` или истёк его срок годности.'
            )
        return data

    def create(self, validated_data):
        return validated_data


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('name', 'slug')
        model = Category


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('name', 'slug')
        model = Genre


class GenreTitleSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = GenreTitle


class TitleGETSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True, required=False)
    genre = GenreSerializer(many=True, read_only=True, required=False)

    def create(self, validated_data):
        genre_data = validated_data.pop('genre') #if 'genre_data' in validated_data else []
        instance = Title(**validated_data)
        title = instance.save()
        for genre in genre_data:
            Title.objects.create(title=title, **genre)

        return title

    class Meta:
        fields = ('id', 'name', 'year', 'rating', 'description', 'genre',
                  'category')
        model = Title


class TitleSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Category.objects.all(),
    )
    genre = serializers.SlugRelatedField(
        many=True,
        queryset=Genre.objects.all(),
        slug_field='slug',
    )

    class Meta:
        fields = ('id', 'name', 'year', 'rating', 'description', 'genre',
                  'category')
        model = Title

    def create(self, validated_data):
        if 'genre' not in self.initial_data:
            titles = Title.objects.create(**validated_data)
            return titles
        genres = validated_data.pop('genre')
        titles = Title.objects.create(**validated_data)
        for genre in genres:
            current_genre = get_object_or_404(Genre, slug=genre)
            GenreTitle.objects.create(genre_id=current_genre, title_id=titles)
        return titles


class UsersSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'username', 'email',
            'first_name', 'last_name',
            'bio', 'role',
        )
        extra_kwargs = {'email': {'required': True}}

    def validate(self, data):
        if User.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError(
                'Пользователь с таким `email` уже зарегистрирован.'
            )
        return data


class MyselfSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'username', 'email',
            'first_name', 'last_name',
            'bio', 'role',
        )
        extra_kwargs = {'role': {'read_only': True}}


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(
        read_only=True,
        slug_field='username',
        default=serializers.CurrentUserDefault()
    )

    def validate(self, data):
        if data['score'] not in range(1, 11):
            raise serializers.ValidationError(
                "Оценка должна быть в диапазоне [1, 10]"
            )
        return data

    class Meta:
        fields = '__all__'
        model = Review
        read_only_fields = ('title_id',)
        validators = [
            UniqueTogetherValidator(
                queryset=Review.objects.all(),
                fields=('author', 'title_id'),
            )
        ]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(
        read_only=True,
        slug_field='username'
    )
    review_id = serializers.SlugRelatedField(
        read_only=True,
        slug_field='slug'
    )

    class Meta:
        fields = '__all__'
        model = Comment
