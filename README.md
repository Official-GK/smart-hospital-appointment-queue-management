# Smart Hospital Appointment & Queue Management System

Development environment is ready.

## Git Workflow

1. `main` is the release/production branch.
2. `develop` is the integration branch.
3. Developers create feature branches from `develop`.
4. Developers work only on their assigned feature branch.
5. Developers commit their changes to their feature branch.
6. Developers push their feature branch to GitHub.
7. Developers create a Pull Request from their feature branch to `develop`.
8. Tech Lead reviews the Pull Request.
9. Changes are merged into `develop` only after approval.
10. `main` should not be directly modified by developers.
11. `main` is updated only when the project is ready for release.

### Pull Request Workflow

```
develop
   ↓
create feature branch
   ↓
developer implements feature
   ↓
developer tests feature
   ↓
commit changes
   ↓
push feature branch
   ↓
Pull Request → develop
   ↓
Tech Lead review
   ↓
Changes requested OR approved
   ↓
Merge into develop
```
