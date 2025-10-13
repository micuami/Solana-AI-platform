import React from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Databases({ token }) {
  const [dbs, setDbs] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:5001/databases/databases", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.json())
      .then(data => setDbs(data || []))
      .catch(err => console.error(err));
  }, [token]);

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Databases</h2>
        <Link to="/upload/db" className="bg-green-600 text-white px-3 py-1 rounded">Upload Database</Link>
      </div>
      <ul className="space-y-2">
        {dbs.map(d => (
          <li key={d.id} className="border p-2 rounded">{d.name} - {d.description}</li>
        ))}
      </ul>
    </div>
  );
}
