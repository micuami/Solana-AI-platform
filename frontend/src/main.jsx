import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Models from "./pages/Models";
import Databases from "./pages/Databases";
import UploadModel from "./pages/UploadModel";
import UploadDatabase from "./pages/UploadDatabase";
import ProtectedRoute from "./components/ProtectedRoute";

import "./index.css";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || null);

  return (
    <Router>
      <Navbar token={token} setToken={setToken} />
      <Routes>
        <Route path="/login" element={<Login setToken={setToken} />} />
        <Route path="/models" element={<ProtectedRoute token={token}><Models token={token} /></ProtectedRoute>} />
        <Route path="/databases" element={<ProtectedRoute token={token}><Databases token={token} /></ProtectedRoute>} />
        <Route path="/upload/model" element={<ProtectedRoute token={token}><UploadModel token={token} /></ProtectedRoute>} />
        <Route path="/upload/db" element={<ProtectedRoute token={token}><UploadDatabase token={token} /></ProtectedRoute>} />
        <Route path="*" element={<p className="p-4">Page not found</p>} />
      </Routes>
    </Router>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
