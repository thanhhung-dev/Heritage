import React from 'react';

export default function ExplorePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] pt-28 text-center px-4">
      <h1 className="text-3xl font-serif font-bold text-white mb-3">
        Không gian Khám phá Di sản
      </h1>
      <p className="text-gray-400 max-w-md">
        Tính năng khám phá kho tàng di sản văn hóa đang được kết nối dữ liệu và phát triển.
      </p>
      <div className="mt-4 px-3 py-1 text-xs rounded-full bg-stone-800 text-amber-500 border border-stone-700">
        Tính năng đang hoàn thiện
      </div>
    </div>
  );
}