import { initializeApp } from "https://www.gstatic.com/firebasejs/12.1.0/firebase-app.js";

const firebaseConfig = {
  apiKey: "AIzaSyB8GsUB1Rm5d7x--_4b9Ch8J1tr4PQwlZM",
  authDomain: "haianh-web.firebaseapp.com",
  projectId: "haianh-web",
  storageBucket: "haianh-web.firebasestorage.app",
  messagingSenderId: "501490561221",
  appId: "1:501490561221:web:16c7333c43a67cae4080ac"
};

const app = initializeApp(firebaseConfig);

export { app };