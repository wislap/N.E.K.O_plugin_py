import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ZoneCard } from '@/components/ZoneCard';
import { zones as fallbackZones } from '@/data';
import { zonesApi } from '@/services/api';
import type { Zone } from '@/types';
import { listContainer } from '@/lib/animations';
import { isDebugDataEnabled } from '@/lib/debug';
import { logError } from '@/lib/error-reporting';

export function ZonesSection() {
  const [zones, setZones] = useState<Zone[]>(
    isDebugDataEnabled ? fallbackZones : []
  );

  useEffect(() => {
    let isMounted = true;

    zonesApi.list()
      .then((data) => {
        if (isMounted && data.length > 0) {
          setZones(data);
        }
      })
      .catch((error) => {
        logError(error, {
          title: '首页分区加载失败',
          severity: 'warn',
          context: {
            module: 'home',
            action: 'loadZones',
            fallbackEnabled: isDebugDataEnabled
          }
        });
        if (isMounted && isDebugDataEnabled) {
          setZones(fallbackZones);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="py-20 bg-[#0F0F1A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-4">
            浏览分区
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            按功能分区浏览插件，快速找到你需要的功能
          </p>
        </div>

        <motion.div
          variants={listContainer}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true, margin: '-80px' }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
        >
          {zones.map((zone) => (
            <ZoneCard key={zone.id} zone={zone} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}
