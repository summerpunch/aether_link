from injector import Injector, Module, singleton, provider
from src.store.database_manager import DatabaseManager
from src.engine.tools.builtin.provider_manager import BuiltinProviderManager
from src.engine.language_model.language_model_manager import LanguageModelManager


class AppModule(Module):
    @singleton
    @provider
    def provide_database_manager(self) -> DatabaseManager:
        from src.store import database_manager
        return database_manager.init_database_manager()

    @singleton
    @provider
    def provide_builtin_provider_manager(self) -> BuiltinProviderManager:
        return BuiltinProviderManager()

    @singleton
    @provider
    def provide_language_model_manager(self) -> LanguageModelManager:
        return LanguageModelManager()


injector = Injector([AppModule()])
