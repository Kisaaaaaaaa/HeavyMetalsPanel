#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试analyze路由500错误的脚本
"""

import os
import sys
import traceback

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_analyze_route_with_error_capture():
    """测试analyze路由并捕获详细错误"""
    print("开始测试analyze路由并捕获错误...")
    
    try:
        from app import app, analyze
        print("✅ 成功导入analyze函数")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 创建测试上下文
    with app.test_request_context():
        # 模拟session
        with app.test_client() as client:
            # 先登录获取session
            response = client.post('/', data={
                'username': 'test',  # 假设存在test用户
                'password': 'test'
            }, follow_redirects=True)
            
            if response.status_code == 200:
                print("✅ 登录成功")
                
                # 测试analyze路由并捕获错误
                try:
                    response = client.get('/analyze')
                    print(f"Analyze路由状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("✅ Analyze路由访问成功")
                        return True
                    else:
                        print(f"❌ Analyze路由访问失败: {response.status_code}")
                        print(f"响应内容: {response.get_data(as_text=True)}")
                        return False
                        
                except Exception as e:
                    print(f"❌ Analyze路由访问异常: {e}")
                    print("详细错误信息:")
                    traceback.print_exc()
                    return False
            else:
                print("❌ 登录失败，无法测试analyze路由")
                return False

def test_template_rendering():
    """测试模板渲染"""
    print("\n开始测试模板渲染...")
    
    try:
        from app import app
        from flask import render_template
        
        # 测试模板是否存在
        template_path = os.path.join('templates', 'analyze.html')
        if os.path.exists(template_path):
            print(f"✅ 模板文件存在: {template_path}")
        else:
            print(f"❌ 模板文件不存在: {template_path}")
            return False
        
        # 测试模板渲染
        with app.test_request_context():
            try:
                # 使用测试数据渲染模板
                test_data = {
                    'user_data': [],
                    'map_data': [],
                    'metal_stats': [],
                    'exceed_stats': {}
                }
                
                html = render_template('analyze.html', **test_data)
                print("✅ 模板渲染成功")
                print(f"渲染的HTML长度: {len(html)} 字符")
                return True
                
            except Exception as e:
                print(f"❌ 模板渲染失败: {e}")
                print("详细错误信息:")
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ 模板测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("测试Analyze路由500错误")
    print("=" * 60)
    
    # 测试模板渲染
    template_success = test_template_rendering()
    
    # 测试analyze路由
    route_success = test_analyze_route_with_error_capture()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"模板渲染: {'✅ 成功' if template_success else '❌ 失败'}")
    print(f"Analyze路由: {'✅ 成功' if route_success else '❌ 失败'}")
    
    if template_success and route_success:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

