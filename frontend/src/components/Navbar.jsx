import React from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Navbar({ token, setToken }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    navigate("/login");
  };

  return (
    <nav className="bg-gray-800 p-4 text-white flex justify-between">
      <div className="space-x-4">
        <Link to="/models" className="hover:underline">Models</Link>
        <Link to="/databases" className="hover:underline">Databases</Link>
      </div>
      {token ? (
        <button onClick={handleLogout} className="bg-red-600 px-3 py-1 rounded">Logout</button>
      ) : (
        <Link to="/login" className="hover:underline">Login</Link>
      )}
    </nav>
  );
}
