# CHANGELOG

<!-- version list -->

## v1.5.2 (2026-11-14)

### Bug Fixes

- Encode database URL credentials safely
  ([`36b7fbc`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/36b7fbca85bb56a7ae7f3bf749b86967dbcc66d6))


## v1.5.1 (2026-11-13)

### Bug Fixes

- Accept water_level as an alias for distance_cm
  ([`3482c6c`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/3482c6c4bb8124d445174d227bb6e1857b806d67))

- Annotate Boolean actuator columns as bool
  ([`def2cce`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/def2cce7727fd88e5183dec0acf92eae7acd5ef5))

- Centralize password hashing in a security utility
  ([`a4cf2fa`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/a4cf2fa268b0b0edcedf95e25343a47df2f308d6))

- Make nutrition_id required on the profile output schema
  ([`9e0030c`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/9e0030c64e93e9e6b598ec34a7231dc7a018824b))

- Read JWT key files lazily instead of at import
  ([`10aabe7`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/10aabe77df57993c69d8058a4abc31588b08d0c4))

- Rebuild DATABASE_URL from parts and gate CORS credentials
  ([`60ee2f3`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/60ee2f370d47d32ca7de8e0d9e4a209e627106a9))

- Return the log delete response with the detail field
  ([`4eeae88`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/4eeae88cad45b333e28cc23ecb08c6802ac662f8))

- Source the CoAP actuator client and tuning from Settings
  ([`b98b5fe`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/b98b5fe309f94170f08d76875b6e5188c016a78c))

- Type the actuator profile as PlantNutritionProfileOut
  ([`886893c`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/886893c9fd9bbb42635e08b88e912c72cd74180f))

- **audit**: Harden actuator delivery and service observability
  ([`d1c8754`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/d1c87545087fc322ddb800211c33e71c71a39411))

### Documentation

- Document the CoAP instance registry limitation
  ([`f49d866`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/f49d866d3b4a3b71df57a0f355ce685a35776f1f))

- Document the test workflow, root pytest config and JWT key resolution
  ([`9e2ab88`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/9e2ab888f8d8926f1a8a9ffddb28a8bd88e9f0d2))

- Standardize on the repository-root .env and backend commands
  ([`7609036`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/7609036de2e16f3e8b3a6346cf0dc79fdd58de55))


## v1.5.0 (2026-10-20)

### Bug Fixes

- Prevent data loss and stabilize real-time monitoring pipeline under load
  ([`955838b`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/955838bb14492d09a22aaaa57d2fd117e33bd74a))

- Stabilize CoAP handler and aggregator with tests & logging
  ([`9c65e34`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/9c65e34d18d6da9f773e05c9f872ece7a6bd626f))

- **infra**: Update database connection config and docker port mapping
  ([`f0bdf65`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/f0bdf65a12ac753a28c7b3581d82f220862cf5a7))

### Features

- Add structured system log feature with enums + REST endpoints + TimescaleDB hypertable
  ([`bd897e4`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/bd897e45de742f99dfb849c1a22e25e688974d2e))


## v1.4.1 (2026-08-12)

### Bug Fixes

- Add skip ci tag to semantic release commit message
  ([`be35dfb`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/be35dfb58dc59685ce92f5cde9b5890271fa3548))


## v1.4.0 (2026-08-11)

### Bug Fixes

- Update docstring for control_hydroponic_actuators to reflect CoAP Observe
  ([`ad2c06a`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/ad2c06a260572b3fcb354962f8ec28bec06ec18c))

### Features

- Add actuator status fields to hydroponics latest response schema
  ([`f448f96`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/f448f96d555272720b33485da6522145df66871c))


## v1.3.2 (2026-08-07)

### Bug Fixes

- Fix CoAP Observe notifications handling and logging
  ([`37a9b85`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/37a9b85e6f6e51fae8e0ef9c20b9e2cafba1fe94))

- Update docstring for control_hydroponic_actuators to reflect CoAP Observe
  ([`de80c96`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/de80c96c15359c3ed4cc9fd352d3a143258172c5))


## v1.3.1 (2026-08-07)

### Bug Fixes

- Update docstring for control_hydroponic_actuators to reflect CoAP Observe
  ([`0e5f90a`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/0e5f90ae7c83331b4ce1f5866ce2f6d49da9dbe1))


## v1.3.0 (2026-08-06)

### Documentation

- Migrate and expand smart hydroponic guide
  ([`f94601a`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/f94601aafc7f9abbf0b5238cf17bfa95e00d0824))

- Migrate and expand smart hydroponic guide
  ([`39dd3bc`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/39dd3bc5ef99eae2c43aa1a6362464670e00a5c7))

- **shared**: Add roadmap tracker, fuzzy logic guide, and AI agent configuration
  ([`32b61b7`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/32b61b7e5a925d480600b8ab44a0c3dfb19d16c6))

- **shared**: Move roadmap tracker to root directory
  ([`07dc196`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/07dc196f2b94e0b80b43a820027bc8afd674e722))

### Features

- Refactor actuator control to server-centric CoAP observe pattern
  ([`81e3703`](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/81e370345dfb32e1f6942afdb442aea3e866423f))


## v1.2.0 (2026-05-19)

### Features

- Add nutrition profile
  ([`9fabd36`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/9fabd36b798f41d01ac44fdc5b354c293cd6955c))

- **analytics**: Use public hydroponic data endpoint
  ([`7075392`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/70753929d2fbea666ec86a5fa37dc20441495531))


## v1.1.0 (2026-04-17)

### Features

- Fix newline
  ([`0f191ad`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/0f191ad4c410ee10e5969718186485eb4b59dfba))


## v1.0.0 (2026-04-15)

- Initial Release

## v2.0.0

- Initial stable release for the backend application.

## v1.0.0-beta.14 (2026-04-09)

### Features

- Change password and auto revoke token
  ([#21](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/21),
  [`62776c0`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/62776c0840e7105289aa33351dd0b2ed2758160b))


## v1.0.0-beta.13 (2026-04-08)

### Bug Fixes

- Ph and tds fiels in backend. Add index column, fix data retrieve and hide control panel from guest
  ([#20](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/20),
  [`37bcdfb`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/37bcdfbca814a93ae5208173e7e4f788f9e4b765))


## v1.0.0-beta.12 (2026-04-07)

### Features

- Add HydroponicDashboardOut schema and update latest data endpoint
  ([#19](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/19),
  [`55e0b28`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/55e0b280ccad89ba1b8237dfcc7462c77b11635e))


## v1.0.0-beta.11 (2026-04-07)

### Features

- Update some features and synchronize all
  ([`b4a95ac`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/b4a95acf9e7249e9671285ad3b32caec5a23482b))


## v1.0.0-beta.10 (2026-04-06)

### Features

- User services, enhance auth flow, improve API tests and add graphs for analysis
  ([#18](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/18),
  [`e658c4c`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/e658c4c49b72b48820e380720307098027339d07))


## v1.0.0-beta.9 (2026-04-06)

### Features

- **backend**: Add role-based authorization, improve user auth flow, and add API tests
  ([#16](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/16),
  [`10f29c7`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/10f29c7327e7c217c5a578ab31553b02b3269bac))


## v1.0.0-beta.8 (2026-03-28)

### Features

- Update user schema, implement timestamp utils, and cleanup legacy database
  ([#15](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/15),
  [`7e9fd79`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/7e9fd795252f1e6232870094ba9750218c717b2f))


## v1.0.0-beta.7 (2026-01-27)

### Bug Fixes

- Update API documentation link in index.html
  ([#14](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/14),
  [`887b5c7`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/887b5c7aa7013a22932bcb0058342baff25fa954))

### Features

- Add superuser creation, role management and enhance logging
  ([#14](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/14),
  [`887b5c7`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/887b5c7aa7013a22932bcb0058342baff25fa954))


## v1.0.0-beta.6 (2026-01-26)

### Bug Fixes

- Docker repository name ([#13](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/13),
  [`0bfb36d`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/0bfb36d78ea5bfa909db9e36a7db766043c3f38a))


## v1.0.0-beta.5 (2026-01-26)

### Bug Fixes

- Branch ref for docker push
  ([#12](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/12),
  [`e61dbab`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/e61dbab201af2d8c2db2d0962a523c1a96416624))


## v1.0.0-beta.4 (2026-01-26)

### Bug Fixes

- Docker github actions condition
  ([#11](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/11),
  [`b9b2ceb`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/b9b2cebbf46ed682f79de91203f74175da3e84cd))


## v1.0.0-beta.3 (2026-01-26)

### Bug Fixes

- Trigger docker push ([#10](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/10),
  [`4921369`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/4921369303f3bc8a2f9e17482e2f8bcf9224d077))


## v1.0.0-beta.2 (2026-01-26)

### Bug Fixes

- CI/CD workflows for Docker image build and release process
  ([#9](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/pull/9),
  [`c35bdca`](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/c35bdcac8e9dcab7e8cb53c5e26c5eb875976a20))


## v1.0.0-beta.1 (2026-01-25)

- Initial Release
