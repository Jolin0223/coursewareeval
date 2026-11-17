# 主按钮前景色组件包 2.2.3

运行时部署 standard-icon.css 即可。SVG已内嵌，manifest与svg目录仅供开发维护。

变化仅为主按钮 color 使用 var(--cb-primary-ink, #fff)；未设置变量时保持默认白色。源码头部沿用基线注释，交付版本与SHA256以manifest为准。

浅底按钮在实际按钮或容器设置 --cb-primary-ink: #333333；普通按钮仍使用 --cb-ink。课件自身若硬编码更高优先级白色，须同步修正其局部样式。

全包交付说明包含历史影响和测试边界。此文件尚未上传CDN。
