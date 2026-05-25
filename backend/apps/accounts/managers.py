from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, matricule, email, password, **extra_fields):
        if not matricule:
            raise ValueError("The matricule field must be set.")
        if not email:
            raise ValueError("The email field must be set.")

        extra_fields.setdefault("business_identity", "STUDENT")
        extra_fields.setdefault("account_status", "ACTIVE")

        email = self.normalize_email(email)
        user = self.model(email=email, matricule=matricule, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, matricule, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(matricule, email, password, **extra_fields)

    def create_superuser(self, matricule, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("business_identity", "ADMINISTRATIVE_STAFF")
        extra_fields.setdefault("account_status", "ACTIVE")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(matricule, email, password, **extra_fields)
