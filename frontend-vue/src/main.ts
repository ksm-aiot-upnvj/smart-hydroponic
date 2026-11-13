import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import { configureHttpClient } from "./http";

// Must run before any API call is issued (M-3).
configureHttpClient();

const app = createApp(App);

app.use(router);
app.mount("#app");
