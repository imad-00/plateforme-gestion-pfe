import SideBar from "../../../components/SideBar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <SideBar role="admin" />
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}