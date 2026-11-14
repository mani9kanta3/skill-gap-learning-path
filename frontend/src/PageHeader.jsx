import React from "react";

/*
  The title row at the top of every page: a small label for the section,
  the page title, one line saying what the page is for, and room on the
  right for buttons.
*/
function PageHeader({ eyebrow, title, subtitle, children }) {
  return (
    <div className="page-head">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {children && <div className="d-flex gap-2">{children}</div>}
    </div>
  );
}

export default PageHeader;
