export interface HeritageItemMock {
  id: string;
  name: string;
  location: string;
  category: 'Phi vật thể' | 'Vật thể' | 'Danh thắng';
  status: 'Đã duyệt' | 'Đang rà soát';
  thumbnailUrl?: string;
}

export const MOCK_HERITAGE_ITEMS: HeritageItemMock[] = [
  {
    id: 'h-01',
    name: 'Nhã nhạc Cung đình Huế',
    location: 'Thừa Thiên Huế',
    category: 'Phi vật thể',
    status: 'Đã duyệt',
  },
  {
    id: 'h-02',
    name: 'Danh thắng Ngũ Hành Sơn',
    location: 'Đà Nẵng',
    category: 'Danh thắng',
    status: 'Đã duyệt',
  },
  {
    id: 'h-03',
    name: 'Nghệ thuật Bài Chòi Trung Bộ',
    location: 'Đà Nẵng - Huế - Quảng Nam',
    category: 'Phi vật thể',
    status: 'Đang rà soát',
  },
];

/**
 * Hàm mock API giả lập gọi lấy danh sách di sản (có hỗ trợ độ trễ mạng)
 */
export async function fetchMockHeritageList(delayMs = 300): Promise<HeritageItemMock[]> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_HERITAGE_ITEMS);
    }, delayMs);
  });
}