// Configuration Firebase pour le Dashboard Live Score
import { initializeApp } from "firebase/app";
import { getDatabase } from "firebase/database";

const firebaseConfig = {
  apiKey: "AIzaSyB1Qq51GUOg54VPGg5KTZu2R97lzKTDya4",
  authDomain: "api-ffhockey.firebaseapp.com",
  projectId: "api-ffhockey",
  storageBucket: "api-ffhockey.firebasestorage.app",
  messagingSenderId: "1082868024477",
  appId: "1:1082868024477:web:b191e554613796c6d88074",
  databaseURL: "https://api-ffhockey-default-rtdb.europe-west1.firebasedatabase.app"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Realtime Database
export const database = getDatabase(app);
