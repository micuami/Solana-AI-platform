import React from "react";
import { Link } from "react-router-dom";

const Home = () => {
    return (
        <div className="home-container">
            <h1 className="heading">Welcome to CortexHub!</h1>
            <Link to="/signup" className="btn btn-primary btn-lg">Get started</Link>
        </div>
    );
}

export default Home;