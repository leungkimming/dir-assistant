# Solution Design
## API
* Controllers: API entry point with access control
* Program.cs: AddAutoMapper
* RegisterModule.cs: Register Repositories and Services for Dependency Injection in Constructors
* Authorization: The policy based authorization framework is already completed. You just need to specify [AccessCodeAuthorize("XXNN")] in controllers where XX is the role and NN is the access level.
## Business
* Persistence Ignorance Business Entities with properties and business rule methods
## Common
* DTOs: API Requests & Responses transfer objects
* Inherit from DTObaseRequest, DTObase with the Refresh function.
## Data
### EF: Entityframework
* Interfaces: Repository Interface
* Repositories: Repositories implementing the Interface
* EFContext.cs: DataBase Schema
* IUnitOfWork.cs & UnitOfWork.cs: Need to include all repositories
### CQRS: command query responsibility segregation (CQRS) pattern. It should only contain Queries.
## DocumentProcessing: Telerik.Windows.Documents helpers
## Migrator: SQL DB Code First pattern
* Migrations: Perforom DB Migration in case of schema changes
## Service
* MapperProfiles: AutoMapper for DB to Entity model translation
* Actual service implementations for API Controllers