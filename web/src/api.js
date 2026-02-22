import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5001",
});

export const getStatus = () => api.get("/status");

export const alarmOn = () => api.post("/alarm/on", {});
export const alarmOff = () => api.post("/alarm/off", {});

export const armSystem = () => api.post("/system/arm", {});
export const disarmSystem = () => api.post("/system/disarm", {});

export const sendDmsKey = (key) => api.post("/dms/key", { key });

export const setTimer = (seconds) => api.post("/timer/set", { seconds });
export const setTimerAddN = (add_n) => api.post("/timer/config", { add_n });
export const timerAdd = () => api.post("/timer/add", {});

export const setRgb = (payload) => api.post("/rgb", payload);

export const scenarioPi1Entry = () => api.post("/scenario/pi1_entry", {});
export const scenarioPi1Exit = () => api.post("/scenario/pi1_exit", {});
