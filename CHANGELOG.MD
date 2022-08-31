
# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
 
[comment]: <> (## [Unreleased] - yyyy-mm-dd)
 
[comment]: <> (Here we write upgrading notes for brands. It's a team effort to make them as)

[comment]: <> (straightforward as possible.)
 
[comment]: <> (### Added)

[comment]: <> (- [PROJECTNAME-XXXX]&#40;http://tickets.projectname.com/browse/PROJECTNAME-XXXX&#41;)

[comment]: <> (  MINOR Ticket title goes here.)

[comment]: <> (- [PROJECTNAME-YYYY]&#40;http://tickets.projectname.com/browse/PROJECTNAME-YYYY&#41;)

[comment]: <> (  PATCH Ticket title goes here.)
 
[comment]: <> (### Changed)
 
[comment]: <> (### Fixed)
## [1.2.3] - 31-08-2022 
Bugfix: language not being properly using to select title

## [1.2.2] - 31-08-2022 
Fixed:
Language not being taken into account and additional name for tracks not being properly passed.

## [1.2.0] - 22-07-2022
  
Here we would have the update steps for 1.2.0 for people to follow.

```
pip install --ignore-installed https://github.com/HOZHENWAI/Beets-Plugin_VGMdb
```
### Added

- Nothing

### Changed
  
- [Beets-Plugin_VGMdb]
  Artist priority is now definable in the config with the key artist-priority, it expect a comma seperated string 
 
### Fixed
 
- [Beets-Plugin_VGMdb]
  Bug when no artist information could be found using vgmdb.info api.
  

## [1.1.2] - 31-05-2022
  
Here we would have the update steps for 1.1.2 for people to follow.

```
pip install --ignore-installed https://github.com/HOZHENWAI/Beets-Plugin_VGMdb
```
### Added

- Nothing

### Changed
  
- [Beets-Plugin_VGMdb]
  Artist priority now goes Composer->Performer->Arranger
 
### Fixed
 
- [Beets-Plugin_VGMdb]
  Bug when no artist information could be found using vgmdb.info api.
  