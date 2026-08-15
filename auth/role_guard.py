class RoleGuard:
    @staticmethod
    def check_access(user_role, allowed_roles):
        if user_role not in allowed_roles:
            raise PermissionError("Access Denied: You do not have permission to view this module.")
        return True
