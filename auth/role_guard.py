from typing import Sequence


class RoleGuard:
    """Guard that verifies a user's role is in the allowed set."""

    @staticmethod
    def check_access(user_role: str, allowed_roles: Sequence[str]) -> bool:
        """Check if *user_role* is permitted.

        Parameters
        ----------
        user_role : str
            The role of the current user.
        allowed_roles : Sequence[str]
            Roles that are permitted access.

        Returns
        -------
        bool
            ``True`` if access is granted.

        Raises
        ------
        PermissionError
            If *user_role* is not in *allowed_roles*.
        """
        if user_role not in allowed_roles:
            raise PermissionError("Access Denied: You do not have permission to view this module.")
        return True
