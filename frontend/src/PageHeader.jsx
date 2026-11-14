import React from "react";

/*
  The title row at the top of every page: where you are (section / page),
  the page title, one line saying what the page is for, and room on the
  right for buttons.
*/
function PageHeader({ eyebrow, title, subtitle, children }) {
  return (
    <div className="page-head">
      <div>
        {eyebrow && (
          <div className="crumb">
            {eyebrow} / {title}
          </div>
        )}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {children && <div className="d-flex gap-2">{children}</div>}
    </div>
  );
}

export default PageHeader;
