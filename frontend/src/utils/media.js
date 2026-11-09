/**
 * 图片地址清洗：
 * - 后端很多记录的 image 是 "无"、null 或相对路径（且没有挂载静态目录）
 * - 只有可用的 http(s) / data URL 才交给 <img>，其余返回空串走占位样式
 */
export function resolveImage(value) {
  if (!value) return ''
  const url = String(value).trim()
  if (!url) return ''
  if (['无', 'none', 'null', 'undefined', '-'].includes(url.toLowerCase())) return ''

  if (/^(https?:)?\/\//i.test(url) || url.startsWith('data:image/')) return url
  return ''
}

/** 头像同理，默认值 file\p1.jpg 并不是可访问地址 */
export function resolveAvatar(value) {
  return resolveImage(value)
}
