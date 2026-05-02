import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Grid3X3, List, SlidersHorizontal } from 'lucide-react';
import { PluginCard } from '@/components/PluginCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { zones } from '@/data';
import { pluginsApi } from '@/services/plugins';
import type { Plugin } from '@/types';
import { listContainer, softReveal } from '@/lib/animations';
import { getErrorMessage, reportError } from '@/lib/error-reporting';

type ViewMode = 'grid' | 'list';
type SortOption = 'default' | 'downloads' | 'likes' | 'latest';

export function Plugins() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortOption>('default');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedZone, setSelectedZone] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const itemsPerPage = 9;

  // Initialize from URL params
  useEffect(() => {
    const search = searchParams.get('search');
    const zone = searchParams.get('zone');
    const sort = searchParams.get('sort') as SortOption;

    if (search) setSearchQuery(search);
    if (zone) setSelectedZone(zone);
    if (sort && ['default', 'downloads', 'likes', 'latest'].includes(sort)) {
      setSortBy(sort);
    }
  }, [searchParams]);

  useEffect(() => {
    let isMounted = true;

    async function fetchPlugins() {
      try {
        setIsLoading(true);
        setErrorMessage('');
        const data = await pluginsApi.list({ page_size: 100, sort_by: 'created_at', sort_order: 'desc' });
        if (isMounted) {
          setPlugins(data.items);
        }
      } catch (error) {
        if (isMounted) {
          const message = getErrorMessage(error, '插件列表加载失败');
          setErrorMessage(message);
          setPlugins([]);
        }
        reportError(error, {
          title: '插件列表加载失败',
          context: {
            module: 'plugins',
            action: 'list',
            pageSize: 100
          }
        });
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchPlugins();

    return () => {
      isMounted = false;
    };
  }, []);

  // Filter and sort plugins
  const filteredPlugins = useMemo(() => {
    let result = [...plugins];

    // Filter by zone
    if (selectedZone !== 'all') {
      result = result.filter((p) => p.zone === selectedZone);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.description.toLowerCase().includes(query) ||
          p.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    // Sort
    switch (sortBy) {
      case 'downloads':
        result.sort((a, b) => b.downloads - a.downloads);
        break;
      case 'likes':
        result.sort((a, b) => b.likes - a.likes);
        break;
      case 'latest':
        result.sort(
          (a, b) =>
            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
        );
        break;
      default:
        // Default: recommended first, then by downloads
        result.sort((a, b) => {
          if (a.isRecommended && !b.isRecommended) return -1;
          if (!a.isRecommended && b.isRecommended) return 1;
          return b.downloads - a.downloads;
        });
    }

    return result;
  }, [plugins, selectedZone, searchQuery, sortBy]);

  // Pagination
  const totalPages = Math.ceil(filteredPlugins.length / itemsPerPage);
  const paginatedPlugins = filteredPlugins.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams(searchParams);
    if (searchQuery.trim()) {
      params.set('search', searchQuery.trim());
    } else {
      params.delete('search');
    }
    setSearchParams(params);
    setCurrentPage(1);
  };

  const handleZoneChange = (zone: string) => {
    setSelectedZone(zone);
    const params = new URLSearchParams(searchParams);
    if (zone !== 'all') {
      params.set('zone', zone);
    } else {
      params.delete('zone');
    }
    setSearchParams(params);
    setCurrentPage(1);
  };

  const handleSortChange = (sort: SortOption) => {
    setSortBy(sort);
    const params = new URLSearchParams(searchParams);
    if (sort !== 'default') {
      params.set('sort', sort);
    } else {
      params.delete('sort');
    }
    setSearchParams(params);
  };

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">所有插件</h1>
          <p className="text-slate-400">
            共 {filteredPlugins.length} 个插件
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col lg:flex-row gap-4 mb-8">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                type="text"
                placeholder="搜索插件..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#1A1A2E] border-slate-700 text-slate-200 placeholder:text-slate-500 focus:border-ring focus:ring-ring/20"
              />
            </div>
          </form>

          {/* Zone Filter */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 lg:pb-0">
            <Button
              variant={selectedZone === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleZoneChange('all')}
              className={
                selectedZone === 'all'
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800'
              }
            >
              全部
            </Button>
            {zones.map((zone) => (
              <Button
                key={zone.id}
                variant={selectedZone === zone.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleZoneChange(zone.id)}
                className={
                  selectedZone === zone.id
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800'
                }
              >
                {zone.name}
              </Button>
            ))}
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-slate-400" />
            <Select value={sortBy} onValueChange={handleSortChange}>
              <SelectTrigger className="w-40 bg-[#1A1A2E] border-slate-700 text-slate-200">
                <SelectValue placeholder="排序方式" />
              </SelectTrigger>
              <SelectContent className="bg-[#1A1A2E] border-slate-700">
                <SelectItem value="default">默认排序</SelectItem>
                <SelectItem value="downloads">下载量</SelectItem>
                <SelectItem value="likes">点赞数</SelectItem>
                <SelectItem value="latest">最新发布</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-1 bg-[#1A1A2E] rounded-lg p-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setViewMode('grid')}
              className={
                viewMode === 'grid'
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }
            >
              <Grid3X3 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setViewMode('list')}
              className={
                viewMode === 'list'
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Plugin Grid/List */}
        {isLoading ? (
          <div className="text-center py-20">
            <p className="text-slate-400 text-lg">正在加载插件...</p>
          </div>
        ) : errorMessage ? (
          <div className="text-center py-20">
            <p className="text-red-400 text-lg">{errorMessage}</p>
          </div>
        ) : paginatedPlugins.length > 0 ? (
          <motion.div
            variants={listContainer}
            initial="initial"
            animate="animate"
            className={
              viewMode === 'grid'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
                : 'flex flex-col gap-4'
            }
          >
            {paginatedPlugins.map((plugin) => (
              <PluginCard key={plugin.id} plugin={plugin} />
            ))}
          </motion.div>
        ) : (
          <motion.div
            variants={softReveal}
            initial="initial"
            animate="animate"
            className="text-center py-20"
          >
            <p className="text-slate-400 text-lg">没有找到匹配的插件</p>
          </motion.div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-12">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-50"
            >
              上一页
            </Button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <Button
                key={page}
                variant={currentPage === page ? 'default' : 'outline'}
                size="sm"
                onClick={() => setCurrentPage(page)}
                className={
                  currentPage === page
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800'
                }
              >
                {page}
              </Button>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-50"
            >
              下一页
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
