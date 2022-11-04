# WINTRY INTEGRATION FOR SQLMODEL

## Usage

Register the DataContext service and wire up the engine creation

```python
from wintry import App, scoped
from wintrymodels.dbcontext import DataContext, AsyncSQLEngineContext, add_data_context
from sqlmodel.ext.asyncio.session import AsyncSession


# Declare the AppDbContext
@scoped
class AppDbContext(AsyncSession, DataContext):
    def __init__(self):
        super().__init__(AsyncSQLEngineContext.get_client(), expire_on_commit=False)


app = App()

# Register the Context engine
add_data_context(app, AsyncSQLEngineContext, "sqlite:///file.db")
```

We can now access SQLModel funcionalities as usual and have dependency injection, so we can do as follows:

```python
from wintry import controller, get
from sqlmodel import select, SQLModel


class User(SQLModel):
    id: int | None = None
    username: str


@controller
class HeroController(object):
    context: AppDbContext

    @get("/users")
    async def get_users(self) -> list[User]:
        return await self.context.exec(select(User))
```

## A simple UnitOfWork implementation

As we can register our `AppDbContext` as a scoped dependency, we can share it among some
classes, so we can implement a UnitOfWork as follows

```python
from wintry import scoped, controller, post, Path
from wintrymodels.dbcontext import DataContext, AsyncSQLEngineContext
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel
from contextlib import asynccontextmanager


# Declare the AppDbContext
@scoped
class AppDbContext(AsyncSession, DataContext):
    def __init__(self):
        super().__init__(AsyncSQLEngineContext.get_client(), expire_on_commit=False)


# Create two models
class Hero(SQLModel):
    id: int | None = None
    name: str

class City(SQLModel):
    id: int | None = None
    city_name: str

# Create Repositories for each Model
@scoped
class HeroRepository(object):
    def __init__(self, context: AppDbContext):
        self.context = context
    
    async def save(self, hero: Hero):
        self.context.add(hero)
    
    async def get_by_id(self, hero_id: int) -> Hero | None:
        return await self.context.get(Hero, hero_id)

@scoped
class CityRepository(object):
    def __init__(self, context: AppDbContext):
        self.context = context
    
    async def save(self, city: City):
        self.context.add(city)
    
    async def get_by_id(self, city_id: int) -> City | None:
        return await self.context.get(City, city_id)

@scoped
class UnitOfWork(object):
    def __init__(self, context: AppDbContext):
        self.context = context

    async def start(self):
        await self.context.begin()

    async def commit(self):
        await self.context.commit()

    async def rollback(self):
        await self.context.rollback()

    # alternatively run this block as a transaction
    @asynccontextmanager
    async def transaction(self):
        try:
            await self.start()
            yield
        except Exception as e:
            await self.rollback()
            raise e
        finally:
            await self.commit()

# This can be part of our service layer, for example
@scoped
class ChangeHeroNameService:
    def __init__(self, repository: HeroRepository, uow: UnitOfWork):
        self.repository = repository
        self.uow = uow
    
    async def change_hero_name(self, hero_id: int):
        async with self.uow.transaction:
            hero = await self.repository.get_by_id(hero_id)
            if hero is not None:
                hero.name = "New Hero Name"
        # As we run in a transaction, the changes to hero
        # will be committed at block end


# Now wire up in a controller
@controller
class HeroController:
    hero_service: ChangeHeroNameService

    @post("/{hero_id}")
    async def change_hero_name(self, hero_id: int = Path()):
        await self.hero_service.change_hero_name(hero_id)
```