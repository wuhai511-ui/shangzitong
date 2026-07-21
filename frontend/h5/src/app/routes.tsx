import type { RouteObject } from "react-router-dom";
import { DashboardPage } from "../features/dashboard/DashboardPage";

export const routes: RouteObject[] = [
  { path: "/", element: <DashboardPage /> },
  { path: "/funds", element: <div>资金</div> },
  { path: "/planning", element: <div>规划</div> },
  { path: "/alerts", element: <div>提醒</div> },
  { path: "/me", element: <div>我的</div> },
];
