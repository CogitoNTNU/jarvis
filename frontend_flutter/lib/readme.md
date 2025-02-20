# Coding principles
## Architecture - Clean code and solid principles
### Folder structure
- Separated into features.
    - Each feature has 3 subfolders
        - Data
        - Domain
        - Presentation
See [Clean code blog post](https://codilime.com/blog/clean-architecture/) for more information on clean code and solid principles.
## Builds and multi-platform
### Flutter flavors
Flutter supports custom build-logic for each platform.
This lets us create and deploy a web-app variant that's gracefully missing local file and folder CRUD with minimal config changes.
Thus we can create native apps that has functionality based on which platform jarvis is running, without it significantly complicating the code-base.
Following CC design a file/folder CRUD api for the AI system would simply be a feature that's enabled on the native Windows build and disabled on the Web build.