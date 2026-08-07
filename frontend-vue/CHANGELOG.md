## [1.4.0](https://github.com/ksm-aiot-upnvj/smart-hydroponic/compare/frontend-v1.3.0...frontend-v1.4.0) (2026-08-06)

## [1.3.0](https://github.com/ksm-aiot-upnvj/smart-hydroponic/compare/frontend-v1.2.0...frontend-v1.3.0) (2026-08-06)

### Bug Fixes

- resolve missing nutrition service calls and update api generated models ([87e7ffb](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/87e7ffb50ccf1b4024dff22d305482fb66eed5e6))
- resolve server deployment errors and apply formatter ([11cfc26](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/11cfc26f0b4e1ededb2f000c2c2f778f2ef17baf))
- resolve server deployment errors and apply formatter ([d2f6b7c](https://github.com/ksm-aiot-upnvj/smart-hydroponic/commit/d2f6b7c82406f4b955d95d15a03bc2874f4aecf8))

## [1.2.0](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/compare/frontend-v1.1.0...frontend-v1.2.0) (2026-05-19)

## [1.1.0](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/compare/frontend-v1.0.0...frontend-v1.1.0) (2026-04-17)

### Features

- fix web title and icon ([e210f60](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/e210f60ebed05d6b63533b4ec7e329d70f5f29df))

## 1.0.0 (2026-04-15)

### Features

- add authentication client with register, login, and protected access functionality ([c82252c](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/c82252cb76217908a88d1d3440966cf27015aa77))
- add data caching and insertion utilities for sensor data ([7a17d97](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/7a17d977d556bd3e0c0b2b6bbc32166848632165))
- add GitHub Actions workflow for documentation deployment and create mkdocs configuration ([9d39188](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/9d39188330a72c5ed26ea5b4ff692623d007f8f0))
- add github workflow (main) ([e889c9f](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/e889c9f7f77feacb16a723cd90b87fc9cb1df17d))
- add JWT authentication middleware for token verification ([09a8673](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/09a8673968b1c284a0148d7d597246550b9ac849))
- add logging info ([b0c45c0](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/b0c45c07327b474e8f5ffcec7c8171751e0f2e85))
- add new actuator, environment, and sensor data handling routes and controllers ([7f6f61b](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/7f6f61bd06c69236c5bcc6d3663fd84637e060ee))
- add resource monitoring ([e2ce66b](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/e2ce66bd51b727fac174dd826eb9eab651413c83))
- add user model and authentication routes for registration and login ([5479639](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/54796395c07cff5636df37be3bb8070405db909c))
- change migrations from sql file to node-pg-migrate ([873a32e](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/873a32e4ca3920c715f2a198f0cc517ca25a241d))
- create user_data table and add authentication route ([0fc247d](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/0fc247d992f044ce3f7431791d6a2efbfee85710))
- implement API request utility and update data fetching logic for sensors, environment, and actuators ([dcc7a85](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/dcc7a85c7b70fb5756d19aace8b6f2ca526f442a))
- implement user authentication with registration and login functionality ([331e8cd](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/331e8cd3761307053b96eccfb31d53c9d31fb997))
- implement WebSocket server for real-time data updates and client communication ([47dfab8](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/47dfab8a975547a5b78bb934e2e7545354cd741d))
- update dependencies for bcryptjs, body-parser, jsonwebtoken, and uuid ([5fd3972](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/5fd3972d8b94fd9553bb2d7e489cd7bfdda54b75))

### Bug Fixes

- add type of payload ([3af9522](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/3af9522180e4436696b3650b14c12ac1f0569e5b))
- column name and ESP32 control flow ([a549fd1](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/a549fd17e0ecada655b574f320f51f81c6bc7651))
- enable manual workflow dispatch and update dependency installation command ([aaf990f](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/aaf990f4c8b2010e9921c41b85591c9ce1f2f1dc))
- fix data flow from microcontroller to server ([131419c](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/131419c065e791cbe3a00b742e325a66846530e9))
- **frontend:** add conventional commits preset for semantic-release ([#23](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/issues/23)) ([db6f480](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/db6f480ad28579290490901d9d0b69d1f93b10d9))
- integrate data from ESP32 to ESP8266 ([d0664cd](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/d0664cd510fe27b7c4acf9e5c8da8024db2c6cce))
- logging info for debugging and compress logs file ([c6ec5ec](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/c6ec5ec286d9b01e423017631ba13712d5ee1ae4))
- refine workflow trigger paths for documentation deployment ([da0fecf](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/da0fecfa4b03c7c854cb37ce33756d0d79d2ced6))
- set default values for ph and tds in sensor data ([fbbe04a](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/fbbe04a97aa75d58773796d69bd83679ed21e7ce))
- streamline Python setup and dependency installation in documentation deployment workflow ([b605f38](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/b605f38027a2cc1b2ee7d4e031f72d507b8c66c8))
- type data for column water ([d5e060b](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/d5e060b1d3750e3f6942cd082696277487ea2f0a))
- typo colomn name for actuator ([d402581](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/d40258104375fd9a643191eef24c83490f96ed60))
- update API endpoint URLs and improve WebSocket integration for real-time command handling ([f46fdf0](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/f46fdf0712bf6b296f75946903b1bd9196a1f0b1))
- update compression policy interval for sensor, environment, and actuator data tables ([54d79f0](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/54d79f077d56365aecc14553a65339fad23388d6))
- update plant data insertion to include pH and TDS values, and replace console.error with deviceLogger ([90a7339](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/90a733936050b717ded2864c23f32e994bd8c2c1))
- update repository name in workflow condition and refine sensor configurations ([b9a07ec](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/b9a07ec771a458a4f6c05c6667857ce5e85b8fda))
- variable from environment JSON ([60c6ac0](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/60c6ac00fb28a737885682e3da5e80451d3436a5))
- websocket connection string ([02893d3](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/02893d3a549da0854c4ccc70989622248a001a2c))
- websocket connection string ([4966055](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/4966055fc43101fb5bd85ea6b5d0ebbc1e1a3cf9))
- Websocket flow, separate controller and routing API ([86b4a0d](https://github.com/IoT-Smart-Hydroponic/smart-hydroponic/commit/86b4a0ddada3bf611abd44ed0110d2335ed57539))

# CHANGELOG

<!-- version list -->

## v2.0.0

- Initial stable release for the frontend-vue application.
