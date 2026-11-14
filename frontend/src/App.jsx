import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";
import Layout from "./Layout";
import Home from "./Home";
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

  There is no login. The actors in the brief (employee, manager, HR
  partner, IT/operations, administrator) are served by pages instead:
  employees and managers use the employee pages, HR uses budgets and
  exceptions, IT and admins use the evaluation page.
*/
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/employees" element={<Employees />} />
          <Route path="/employees/:id" element={<EmployeeDetail />} />
          <Route path="/courses" element={<Courses />} />
          <Route path="/courses/:id" element={<CourseDetail />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/exceptions" element={<Exceptions />} />
          <Route path="/evaluation" element={<Evaluation />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
