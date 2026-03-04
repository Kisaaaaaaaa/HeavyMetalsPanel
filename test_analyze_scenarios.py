#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同用户场景下的analyze页面访问
"""

import requests
import time
import json

def test_different_scenarios():
    """测试不同的用户场景"""
    base_url = "http://127.0.0.1:5000"
    
    print("=" * 80)
    print("测试不同用户场景下的Analyze页面访问")
    print("=" * 80)
    
    # 场景1: 新用户注册并访问
    print("\n场景1: 新用户注册并访问analyze页面")
    try:
        # 注册新用户
        username = f"testuser_{int(time.time())}"
        register_data = {
            'username': username,
            'password': 'testpass'
        }
        
        register_response = requests.post(f"{base_url}/register", data=register_data, timeout=10)
        print(f"注册状态码: {register_response.status_code}")
        
        if register_response.status_code == 200:
            # 登录
            login_data = {
                'username': username,
                'password': 'testpass'
            }
            login_response = requests.post(base_url, data=login_data, timeout=10)
            print(f"登录状态码: {login_response.status_code}")
            
            if login_response.status_code == 200:
                cookies = login_response.cookies
                
                # 访问analyze页面
                analyze_response = requests.get(f"{base_url}/analyze", cookies=cookies, timeout=10)
                print(f"Analyze页面状态码: {analyze_response.status_code}")
                
                if analyze_response.status_code == 200:
                    print("✅ 场景1成功")
                else:
                    print(f"❌ 场景1失败: {analyze_response.status_code}")
                    print(f"错误内容: {analyze_response.text[:500]}")
                    return False
            else:
                print("❌ 登录失败")
                return False
        else:
            print("❌ 注册失败")
            return False
            
    except Exception as e:
        print(f"❌ 场景1异常: {e}")
        return False
    
    # 场景2: 直接访问analyze页面（未登录）
    print("\n场景2: 直接访问analyze页面（未登录）")
    try:
        analyze_response = requests.get(f"{base_url}/analyze", timeout=10)
        print(f"Analyze页面状态码: {analyze_response.status_code}")
        
        if analyze_response.status_code == 302:  # 应该重定向到登录页
            print("✅ 场景2成功（正确重定向）")
        else:
            print(f"❌ 场景2失败: {analyze_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 场景2异常: {e}")
        return False
    
    # 场景3: 使用现有用户访问
    print("\n场景3: 使用现有用户访问analyze页面")
    try:
        # 尝试使用test用户
        login_data = {
            'username': 'test',
            'password': 'test'
        }
        login_response = requests.post(base_url, data=login_data, timeout=10)
        print(f"登录状态码: {login_response.status_code}")
        
        if login_response.status_code == 200:
            cookies = login_response.cookies
            
            # 访问analyze页面
            analyze_response = requests.get(f"{base_url}/analyze", cookies=cookies, timeout=10)
            print(f"Analyze页面状态码: {analyze_response.status_code}")
            
            if analyze_response.status_code == 200:
                print("✅ 场景3成功")
                # 检查页面内容
                content = analyze_response.text
                if "数据分析" in content and "重金属检测平台" in content:
                    print("✅ 页面内容正确")
                else:
                    print("⚠️ 页面内容可能有问题")
            else:
                print(f"❌ 场景3失败: {analyze_response.status_code}")
                print(f"错误内容: {analyze_response.text[:500]}")
                return False
        else:
            print("❌ 登录失败")
            return False
            
    except Exception as e:
        print(f"❌ 场景3异常: {e}")
        return False
    
    return True

def test_with_data():
    """测试有数据情况下的analyze页面"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n" + "=" * 80)
    print("测试有数据情况下的Analyze页面")
    print("=" * 80)
    
    try:
        # 登录
        login_data = {
            'username': 'test',
            'password': 'test'
        }
        login_response = requests.post(base_url, data=login_data, timeout=10)
        
        if login_response.status_code == 200:
            cookies = login_response.cookies
            
            # 多次访问analyze页面
            for i in range(3):
                print(f"\n第{i+1}次访问analyze页面...")
                analyze_response = requests.get(f"{base_url}/analyze", cookies=cookies, timeout=10)
                print(f"状态码: {analyze_response.status_code}")
                
                if analyze_response.status_code != 200:
                    print(f"❌ 第{i+1}次访问失败")
                    print(f"错误内容: {analyze_response.text[:500]}")
                    return False
                else:
                    print(f"✅ 第{i+1}次访问成功")
                
                time.sleep(1)  # 等待1秒
            
            return True
        else:
            print("❌ 登录失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主函数"""
    print("开始测试Analyze页面的不同场景...")
    
    # 等待服务器启动
    time.sleep(2)
    
    # 测试不同场景
    scenarios_success = test_different_scenarios()
    
    # 测试有数据情况
    data_success = test_with_data()
    
    print("\n" + "=" * 80)
    print("测试结果汇总:")
    print(f"不同场景测试: {'✅ 成功' if scenarios_success else '❌ 失败'}")
    print(f"有数据测试: {'✅ 成功' if data_success else '❌ 失败'}")
    
    if scenarios_success and data_success:
        print("\n🎉 所有测试通过！Analyze页面工作正常")
        print("\n如果浏览器仍然显示500错误，可能的原因:")
        print("1. 浏览器缓存问题 - 请清除浏览器缓存")
        print("2. 浏览器Cookie问题 - 请清除浏览器Cookie")
        print("3. 浏览器JavaScript错误 - 请检查浏览器控制台")
        print("4. 网络连接问题 - 请检查网络连接")
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息")
    
    return scenarios_success and data_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
