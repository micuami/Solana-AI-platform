import React, { useState, useContext } from "react";
import { AuthContext } from "../AuthContext";
import { useNavigate } from "react-router-dom";

const Signup = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    try {
      // 1️⃣ Signup
      const signupRes = await fetch("http://127.0.0.1:5001/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });

      if (!signupRes.ok) {
        const errData = await signupRes.json();
        throw new Error(errData.message || "Signup failed");
      }

      // 2️⃣ Login automat după signup
      const loginRes = await fetch("http://127.0.0.1:5001/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier: email, password }),
      });

      if (!loginRes.ok) throw new Error("Login failed");
      const loginData = await loginRes.json();
      login({ username, accessToken: loginData["access token"] });

      navigate("/");
    } catch (err) {
      console.error(err);
      alert(err.message);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-4 border rounded signup-container">
      <h1 className="text-2xl mb-4">Signup</h1>
      <form onSubmit={handleSignup} className="flex flex-col gap-2">
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="border p-2 rounded" required 
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border p-2 rounded" required 
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border p-2 rounded" required 
        />
        <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded mt-2">Signup</button>
      </form>
    </div>
  );
};

export default Signup;