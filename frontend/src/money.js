/*
  Rupees and percentages, written the way people in India read them.

  toLocaleString("en-IN") gives 1,20,00,000 and not 12,000,000. Getting
  the grouping wrong makes a budget look like a different number.
*/

function money(amount) {
  if (amount === null || amount === undefined || amount === "") {
    return "-";
  }

  return `₹${Number(amount).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

/* The same number said out loud: 12000000 becomes "1.2 crore". */
export function inWords(amount) {
  if (amount === null || amount === undefined || amount === "") {
    return "";
  }

  const value = Number(amount);
  const sign = value < 0 ? "-" : "";
  const size = Math.abs(value);

  if (size >= 10000000) {
    return `${sign}${(size / 10000000).toFixed(2).replace(/\.00$/, "")} crore`;
  }
  if (size >= 100000) {
    return `${sign}${(size / 100000).toFixed(2).replace(/\.00$/, "")} lakh`;
  }
  return `${sign}${size.toLocaleString("en-IN")}`;
}

export function percent(value, digits = 1) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

export default money;
