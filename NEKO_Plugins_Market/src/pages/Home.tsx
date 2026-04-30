import { Hero } from '@/sections/Hero';
import { ZonesSection } from '@/sections/ZonesSection';
import { PopularPlugins } from '@/sections/PopularPlugins';
import { LatestPlugins } from '@/sections/LatestPlugins';

export function Home() {
  return (
    <main className="min-h-screen bg-[#0F0F1A]">
      <Hero />
      <ZonesSection />
      <PopularPlugins />
      <LatestPlugins />
    </main>
  );
}