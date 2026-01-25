import { NavLink, useLocation } from 'react-router-dom';
import { Activity, Menu, X } from 'lucide-react';
import { useState, useEffect } from 'react';
import { rem, Box, Button, Group } from '@mantine/core';
import { useMantineTheme, useMantineColorScheme } from '@mantine/core';

export const Navigation = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const theme = useMantineTheme();
  const { colorScheme } = useMantineColorScheme();

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location]);

  const navItems = [
    { to: '/', label: 'Dashboard' },
    { to: '/queues', label: 'Queues' },
    { to: '/workers', label: 'Workers' },
    { to: '/tenants', label: 'Tenants' },
  ];

  return (
    <Box
      component="nav"
      style={{
        backgroundColor: colorScheme === 'dark' ? theme.colors.dark[8] : theme.white,
        borderBottom: `${rem(1)} solid ${
          colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[2]
        }`,
        padding: `${theme.spacing.md} ${theme.spacing.xl}`,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: theme.shadows.sm,
      }}
    >
      <Group justify="space-between" style={{ maxWidth: '1440px', margin: '0 auto', width: '100%' }}>
        <NavLink
          to="/"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: theme.spacing.xs,
            textDecoration: 'none',
            color: colorScheme === 'dark' ? theme.white : theme.black,
            fontWeight: 700,
            fontSize: theme.fontSizes.xl,
          }}
        >
          <Activity size={24} />
          <span>TaskFlow</span>
        </NavLink>

        <Group gap="md" visibleFrom="sm">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                color: isActive
                  ? theme.colors.blue[6]
                  : colorScheme === 'dark'
                  ? theme.colors.gray[0]
                  : theme.colors.gray[7],
                textDecoration: 'none',
                fontWeight: 500,
                padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                borderRadius: theme.radius.sm,
                '&:hover': {
                  backgroundColor:
                    colorScheme === 'dark' ? theme.colors.dark[6] : theme.colors.gray[0],
                },
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </Group>

        <Button
          variant="subtle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          style={{ display: 'none' }}
          hiddenFrom="sm"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </Button>
      </Group>

      {mobileMenuOpen && (
        <Box
          style={{
            position: 'fixed',
            top: '72px',
            left: 0,
            right: 0,
            backgroundColor: colorScheme === 'dark' ? theme.colors.dark[7] : theme.white,
            padding: theme.spacing.md,
            borderTop: `${rem(1)} solid ${
              colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[2]
            }`,
            boxShadow: theme.shadows.sm,
            zIndex: 99,
            display: 'flex',
            flexDirection: 'column',
            gap: theme.spacing.xs,
          }}
        >
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={{
                color: colorScheme === 'dark' ? theme.colors.gray[0] : theme.colors.gray[7],
                textDecoration: 'none',
                padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                borderRadius: theme.radius.sm,
                ':hover': {
                  backgroundColor:
                    colorScheme === 'dark' ? theme.colors.dark[6] : theme.colors.gray[0],
                },
              } as React.CSSProperties}
              onClick={() => setMobileMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </Box>
      )}
    </Box>
  );
};