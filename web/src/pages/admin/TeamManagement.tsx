import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, Space, Drawer } from 'antd';
import { getTeams, createTeam, updateTeam, deleteTeam, getTeam, addTeamMember, updateTeamMemberRole, removeTeamMember } from '@/api/teams';
import type { Team, TeamDetail, TeamMember, TeamRole } from '@/types/team';

const roleLabels: Record<TeamRole, string> = {
  super_admin: '超级管理员',
  org_admin: '组织管理员',
  team_lead: '团队负责人',
  engineer: '工程师',
  analyst: '分析师',
  auditor: '审计员',
};

const TeamManagement: React.FC = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Team | null>(null);
  const [form] = Form.useForm();

  // Member management drawer
  const [detail, setDetail] = useState<TeamDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [memberForm] = Form.useForm();

  const fetchTeams = async () => {
    setLoading(true);
    try {
      const res = await getTeams({ page: 1, page_size: 100 });
      setTeams(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (team: Team) => {
    setEditing(team);
    form.setFieldsValue({ name: team.name, description: team.description });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await updateTeam(editing.id, values);
        message.success('团队已更新');
      } else {
        await createTeam(values);
        message.success('团队已创建');
      }
      setModalOpen(false);
      fetchTeams();
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = async (team: Team) => {
    Modal.confirm({
      title: `删除团队 ${team.name}?`,
      content: '此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteTeam(team.id);
          message.success('团队已删除');
          fetchTeams();
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const openMembers = async (team: Team) => {
    try {
      const d = await getTeam(team.id);
      setDetail(d);
      setDrawerOpen(true);
    } catch {
      message.error('加载成员失败');
    }
  };

  const handleAddMember = async () => {
    if (!detail) return;
    const values = await memberForm.validateFields();
    try {
      await addTeamMember(detail.id, values);
      message.success('成员已添加');
      memberForm.resetFields();
      const d = await getTeam(detail.id);
      setDetail(d);
      fetchTeams();
    } catch {
      message.error('添加失败');
    }
  };

  const handleRoleChange = async (userId: string, role: TeamRole) => {
    if (!detail) return;
    try {
      await updateTeamMemberRole(detail.id, userId, { role_name: role });
      message.success('角色已更新');
      const d = await getTeam(detail.id);
      setDetail(d);
    } catch {
      message.error('更新失败');
    }
  };

  const handleRemoveMember = async (member: TeamMember) => {
    if (!detail) return;
    Modal.confirm({
      title: `移除成员 ${member.display_name}?`,
      okText: '移除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await removeTeamMember(detail.id, member.user_id);
          message.success('成员已移除');
          const d = await getTeam(detail.id);
          setDetail(d);
          fetchTeams();
        } catch {
          message.error('移除失败');
        }
      },
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>团队管理</span>
        <Button type="primary" size="small" onClick={openCreate}>新建团队</Button>
      </div>
      <Table
        size="small"
        loading={loading}
        dataSource={teams}
        rowKey="id"
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '团队名称', dataIndex: 'name', key: 'name' },
          { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
          { title: '成员数', dataIndex: 'member_count', key: 'member_count', width: 80 },
          {
            title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180,
            render: (v: string) => new Date(v).toLocaleString('zh-CN'),
          },
          {
            title: '操作', key: 'action', width: 220,
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => openMembers(record)}>成员</Button>
                <Button size="small" onClick={() => openEdit(record)}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(record)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editing ? `编辑团队: ${editing.name}` : '新建团队'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="团队名称" rules={[{ required: true, message: '请输入团队名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={`成员管理: ${detail?.name || ''}`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={520}
      >
        {/* 添加成员 */}
        <div style={{ marginBottom: 16, padding: 12, background: '#1a1a2e', borderRadius: 8 }}>
          <div style={{ marginBottom: 8, fontWeight: 600, color: '#e2e8f0' }}>添加成员</div>
          <Form form={memberForm} layout="inline" initialValues={{ role_name: 'engineer' }}>
            <Form.Item name="user_id" label="用户ID" rules={[{ required: true }]}>
              <Input placeholder="user_xxx" style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="role_name" label="角色">
              <Select
                style={{ width: 120 }}
                options={(Object.keys(roleLabels) as TeamRole[]).map((r) => ({ value: r, label: roleLabels[r] }))}
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" size="small" onClick={handleAddMember}>添加</Button>
            </Form.Item>
          </Form>
        </div>

        <Table
          size="small"
          dataSource={detail?.members || []}
          rowKey="user_id"
          pagination={false}
          columns={[
            { title: '姓名', dataIndex: 'display_name', key: 'name' },
            { title: '邮箱', dataIndex: 'email', key: 'email', ellipsis: true },
            {
              title: '角色', dataIndex: 'role_name', key: 'role', width: 120,
              render: (role: TeamRole, record) => (
                <Select
                  size="small"
                  value={role}
                  style={{ width: 110 }}
                  onChange={(v: TeamRole) => handleRoleChange(record.user_id, v)}
                  options={(Object.keys(roleLabels) as TeamRole[]).map((r) => ({ value: r, label: roleLabels[r] }))}
                />
              ),
            },
            {
              title: '', key: 'action', width: 60,
              render: (_, record) => (
                <Button size="small" type="link" danger onClick={() => handleRemoveMember(record)}>移除</Button>
              ),
            },
          ]}
        />
      </Drawer>
    </div>
  );
};

export default TeamManagement;
