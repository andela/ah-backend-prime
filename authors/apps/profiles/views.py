from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import (IsAuthenticatedOrReadOnly,
                                        IsAuthenticated
                                        )
from rest_framework.exceptions import NotFound
from authors.apps.authentication.models import User
from authors.apps.authentication.renderers import UserJSONRenderer
from authors.apps.authentication.serializers import UserSerializer
from .permissions import IsOwnerOrReadOnly
from .models import Profile
from .renderers import ProfileJSONRenderer
from .serializers import ProfileSerializer


class ListProfileView(GenericAPIView):
    """
    class that implements fetching all users' profiles
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfileSerializer
    renderer_classes = (ProfileJSONRenderer,)

    def get(self, request, *args, **kwargs):
        queryset = Profile.objects.all()
        serializer = self.serializer_class(
            queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateProfileView(GenericAPIView):
    """
    allows the current user to update their profile
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsOwnerOrReadOnly, ]
    renderer_classes = (ProfileJSONRenderer,)
    lookup_field = "username"

    def get_object(self):
        return get_object_or_404(
            self.get_queryset(),
            user__username=self.kwargs.get("username")
        )

    def put(self, request, *args, **kwargs):
        profile = self.get_object()
        user_name = self.kwargs.get('username')
        logged_in_user = request.user.username
        if str(user_name) == str(logged_in_user):
            serializer = self.serializer_class(
                profile,
                data=request.data
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Profile Updated successfully"})
        else:
            return Response(
                {"message": "You do not have privileges to edit this profile"},
                status=status.HTTP_403_FORBIDDEN
            )


class ProfileRetrieveAPIView(GenericAPIView):
    """
    class handling returning the profile of a single user
    """
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, username, *args, **kwargs):
        '''Function for getting a single users profile'''
        follower = self.request.user.profile

        profile = Profile.objects.select_related('user').get(
            user__username=username)
        following = str(profile.is_followed_by(follower))
        serializer = self.serializer_class(
            profile, context={'request': request})
        data = serializer.data
        data.update({"following": following})
        profile = {'profile': data}
        return Response(profile, status=status.HTTP_200_OK)


class UserListAPIView(GenericAPIView):
    """
    returns list of all users and their profiles
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer
    renderer_classes = (UserJSONRenderer,)

    def get(self, request, *args, **kwargs):
        queryset = User.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileFollowAPIView(GenericAPIView):
    '''This class handles following and unfollowing a user'''
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)

    def delete(self, request, username=None):
        '''This function enables one to unfollow a user'''
        follower = self.request.user.profile

        try:
            followee = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            raise NotFound('A profile with this username was not found.')

        if follower.pk is followee.pk:
            raise serializers.ValidationError('You can not unfollow yourself.')

        if not follower.is_following(followee):
            raise serializers.ValidationError(
                f'You do not follow {followee.user.username}')

        follower.unfollow(followee)

        return Response(
            {"message": f"You have unfollowed {followee.user.username}"},
            status=status.HTTP_200_OK
        )

    def post(self, request, username=None):
        '''This function enables one to follow a user'''
        follower = self.request.user.profile

        try:
            followee = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            raise NotFound('A profile with this username was not found.')

        if follower.pk is followee.pk:
            raise serializers.ValidationError('You can not follow yourself.')

        if follower.is_following(followee):
            raise serializers.ValidationError('You already follow this user')

        follower.follow(followee)

        return Response(
            {"message": f"You are now following {followee.user.username}"},
            status=status.HTTP_201_CREATED
        )


class UserFollowing(GenericAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)

    def get(self, request, username=None):
        '''Method gets users profiles a user follows'''
        user = Profile.objects.get(user__username=username)
        queryset = Profile.objects.filter(followed_by=user.pk)
        serializer = self.serializer_class(
            queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserFollowers(GenericAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)

    def get(self, request, username=None):
        '''Method gets users profiles that follow a user'''
        user = Profile.objects.get(user__username=username)
        queryset = Profile.objects.filter(follows=user.pk)
        serializer = self.serializer_class(
            queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
