import type { RouteObject } from "react-router-dom";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { FundsPage } from "../features/funds/FundsPage";
import { PlanningPage } from "../features/planning/PlanningPage";

export const routes: RouteObject[] = [
  { path: "/", element: <DashboardPage /> },
  { path: "/funds", element: <FundsPage /> },
  { path: "/planning", element: <PlanningPage /> },
  { path: "/alerts", element: <div>提醒</div> },
  { path: "/me", element: <div>我的</div> },
];
