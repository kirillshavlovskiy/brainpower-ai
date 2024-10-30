import * as React from "react";

const Card = React.forwardRef<HTMLDivElement, React.HTMLProps<HTMLDivElement>>((
  { className = "", ...props },
  ref
) => (
  <div
    ref={ref}
    className={`rounded-lg border bg-white shadow p-6 ${className}`}
    {...props}
  />
));

Card.displayName = "Card";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLProps<HTMLDivElement>>((
  { className = "", ...props },
  ref
) => (
  <div
    ref={ref}
    className={`p-6 pt-0 ${className}`}
    {...props}
  />
));

CardContent.displayName = "CardContent";

export { Card, CardContent };