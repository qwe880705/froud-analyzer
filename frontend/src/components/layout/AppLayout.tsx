import { Layout, Menu, Typography } from 'antd'
import {
  DashboardOutlined, AlertOutlined, FolderOpenOutlined,
  UserOutlined, UploadOutlined, AuditOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'

const { Sider, Content, Header } = Layout

const items = [
  { key: '/',       icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/alerts', icon: <AlertOutlined />,     label: 'Alerts' },
  { key: '/cases',  icon: <FolderOpenOutlined />, label: 'Cases' },
  { key: '/users',  icon: <UserOutlined />,       label: 'Users' },
  { key: '/import', icon: <UploadOutlined />,     label: 'Import Data' },
  { key: '/audit',  icon: <AuditOutlined />,      label: 'Audit Log' },
]

export function AppLayout() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const selected = '/' + pathname.split('/')[1]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={210} theme="dark" style={{ position: 'fixed', height: '100vh', zIndex: 10 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #2a2a2a' }}>
          <Typography.Text strong style={{ color: '#fff', fontSize: 13 }}>🔒 Insider Risk</Typography.Text>
          <br />
          <Typography.Text style={{ color: '#777', fontSize: 11 }}>Investigation Assistant</Typography.Text>
        </div>
        <Menu
          theme="dark" mode="inline"
          selectedKeys={[selected === '/' ? '/' : selected]}
          items={items}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8 }}
        />
      </Sider>
      <Layout style={{ marginLeft: 210 }}>
        <Header style={{
          background: '#fff', padding: '0 24px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex', alignItems: 'center',
        }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            ACME Corp · APAC Region · analyst@acme-corp.com
          </Typography.Text>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5', minHeight: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
