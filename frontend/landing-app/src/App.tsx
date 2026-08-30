import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import BroadcastBanner from "./components/BroadcastBanner";
import RoleLoginStrip from "./components/RoleLoginStrip";
import TrustBadges from "./components/TrustBadges";
import Features from "./components/Features";
import WhyChoose from "./components/WhyChoose";
import FeaturesGrid from "./components/FeaturesGrid";
import Security from "./components/Security";
import Roadmap from "./components/Roadmap";
import FAQ from "./components/FAQ";
import CTA from "./components/CTA";
import NextStep from "./components/NextStep";
import Footer from "./components/Footer";

export default function App() {
  return (
    <>
      <BroadcastBanner />
      <Navbar />
      <main>
        <Hero />
        <RoleLoginStrip />
        <TrustBadges />
        <Features />
        <WhyChoose />
        <FeaturesGrid />
        <Security />
        <Roadmap />
        <FAQ />
        <CTA />
        <NextStep />
      </main>
      <Footer />
    </>
  );
}
