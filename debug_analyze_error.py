#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试analyze路由500错误的脚本
"""

import os
import sys
import traceback
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_analyze_route_detailed():
    """详细测试analyze路由并捕获所有可能的错误"""
    print("=" * 80)
    print("详细调试Analyze路由500错误")
    print("=" * 80)
    
    try:
        # 导入Flask应用
        from app import app, create_db_connection, init_db
        print("✅ 成功导入Flask应用")
        
        # 初始化数据库
        print("正在初始化数据库...")
        init_db()
        print("✅ 数据库初始化完成")
        
        # 测试数据库连接
        print("正在测试数据库连接...")
        connection = create_db_connection()
        if connection:
            print("✅ 数据库连接成功")
            connection.close()
        else:
            print("❌ 数据库连接失败")
            return False
        
        # 创建测试客户端
        with app.test_client() as client:
            print("✅ 创建测试客户端成功")
            
            # 测试注册用户
            print("正在注册测试用户...")
            register_response = client.post('/register', data={
                'username': 'testuser',
                'password': 'testpass'
            }, follow_redirects=True)
            print(f"注册响应状态码: {register_response.status_code}")
            
            # 测试登录
            print("正在测试登录...")
            login_response = client.post('/', data={
                'username': 'testuser',
                'password': 'testpass'
            }, follow_redirects=True)
            print(f"登录响应状态码: {login_response.status_code}")
            
            if login_response.status_code == 200:
                print("✅ 登录成功")
                
                # 测试analyze路由
                print("正在测试analyze路由...")
                try:
                    analyze_response = client.get('/analyze')
                    print(f"Analyze路由状态码: {analyze_response.status_code}")
                    
                    if analyze_response.status_code == 200:
                        print("✅ Analyze路由访问成功")
                        print(f"响应内容长度: {len(analyze_response.get_data(as_text=True))}")
                        return True
                    else:
                        print(f"❌ Analyze路由访问失败: {analyze_response.status_code}")
                        print(f"响应内容: {analyze_response.get_data(as_text=True)}")
                        return False
                        
                except Exception as e:
                    print(f"❌ Analyze路由访问异常: {e}")
                    print("详细错误信息:")
                    traceback.print_exc()
                    return False
            else:
                print("❌ 登录失败，无法测试analyze路由")
                print(f"登录响应内容: {login_response.get_data(as_text=True)}")
                return False
                
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        print("详细错误信息:")
        traceback.print_exc()
        return False

def test_database_operations():
    """测试数据库操作"""
    print("\n" + "=" * 80)
    print("测试数据库操作")
    print("=" * 80)
    
    try:
        from app import create_db_connection
        
        connection = create_db_connection()
        if not connection:
            print("❌ 数据库连接失败")
            return False
            
        cursor = connection.cursor(dictionary=True)
        
        # 测试查询用户表
        print("正在查询用户表...")
        cursor.execute("SELECT * FROM users LIMIT 5")
        users = cursor.fetchall()
        print(f"✅ 用户表查询成功，找到 {len(users)} 个用户")
        
        # 测试查询points表
        print("正在查询points表...")
        cursor.execute("SELECT * FROM points LIMIT 5")
        points = cursor.fetchall()
        print(f"✅ points表查询成功，找到 {len(points)} 个点")
        
        # 测试查询water_quality_data表
        print("正在查询water_quality_data表...")
        cursor.execute("SELECT * FROM water_quality_data LIMIT 5")
        wq_data = cursor.fetchall()
        print(f"✅ water_quality_data表查询成功，找到 {len(wq_data)} 条记录")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库操作测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    success = True
    
    # 测试数据库操作
    db_success = test_database_operations()
    success = success and db_success
    
    # 测试analyze路由
    route_success = test_analyze_route_detailed()
    success = success and route_success
    
    print("\n" + "=" * 80)
    print("测试结果汇总:")
    print(f"数据库操作: {'✅ 成功' if db_success else '❌ 失败'}")
    print(f"Analyze路由: {'✅ 成功' if route_success else '❌ 失败'}")
    
    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
