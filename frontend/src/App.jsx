import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";
import Layout from "./Layout";
import Dashboard from "./Dashboard";
import Employees from "./Employees";
import EmployeeDetail from "./EmployeeDetail";
import Courses from "./Courses";
import CourseDetail from "./CourseDetail";
import Budgets from "./Budgets";
import Exceptions from "./Exceptions";
import Evaluation from "./Evaluation";
import NotFound from "./NotFound";

/*
  All the routes.

  There is no login. The actors in the brief are served by sections of
  the sidebar instead: employees and managers use People, HR partners use
  Learning and Budget, IT and operations use Data quality.
*/
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/employees" element={<Employees />} />
          <Route path="/employees/:id" element={<EmployeeDetail />} />
          <Route path="/courses" element={<Courses />} />
          <Route path="/courses/:id" element={<CourseDetail />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/exceptions" element={<Exceptions />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
