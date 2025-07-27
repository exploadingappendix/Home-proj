import { JobForm } from "../components/JobForm";
import Navbar from "@/components/navbar";

export default function NewJobPage() {
  return (
    <main className="p-6 mx-auto">
      <Navbar />
      <h1 className="text-2xl max-w-4xl font-bold mb-6 ">Submit a Training Job</h1>
      <JobForm />
    </main>
  );
}