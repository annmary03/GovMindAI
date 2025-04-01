class AuthRouter:
    """
    A router to control all database operations for different models.
    - Directs Django's authentication models to SQLite.
    - Directs News model queries to MongoDB.
    """

    def db_for_read(self, model, **hints):
        """Point News model reads to MongoDB."""
        if model._meta.app_label == 'newsapp' and model._meta.model_name == 'news':
            return 'mongo'
        return 'default'

    def db_for_write(self, model, **hints):
        """Point News model writes to MongoDB."""
        if model._meta.app_label == 'newsapp' and model._meta.model_name == 'news':
            return 'mongo'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """No cross-database relations."""
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Disallow migrations for MongoDB models."""
        if db == 'mongo':
            return False
        return True