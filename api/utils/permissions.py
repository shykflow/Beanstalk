from rest_framework.permissions import BasePermission

class IsVerifiedPermission(BasePermission):
  def has_permission(self, request, view):
    if request.user.email_verified == False :
      return False
    return True
